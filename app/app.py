from flask import Flask, request, jsonify, render_template, send_from_directory
from pathlib import Path
import subprocess
from datetime import datetime
import os
import json
import logging
from functools import wraps
import threading

app = Flask(__name__)

class KeyManager:
    def __init__(self, keys_dir):
        self.keys_dir = Path(keys_dir)
        self.private_key_path = self.keys_dir / 'local.pem'
        self.public_key_path = self.keys_dir / 'local.pub'
        self._ensure_keypair()
        self._fingerprint = self._calculate_fingerprint()
    
    def _ensure_keypair(self):
        if not self.private_key_path.exists():
            # Generate private key
            subprocess.run([
                'openssl', 'genpkey',
                '-algorithm', 'RSA',
                '-out', str(self.private_key_path),
                '-pkeyopt', 'rsa_keygen_bits:2048'
            ], check=True)
            
            # Extract public key
            subprocess.run([
                'openssl', 'rsa',
                '-in', str(self.private_key_path),
                '-pubout',
                '-out', str(self.public_key_path)
            ], check=True)
    
    def _calculate_fingerprint(self):
        result = subprocess.run(
            ['openssl', 'dgst', '-sha256', '-r', str(self.public_key_path)],
            capture_output=True, text=True, check=True
        )
        return result.stdout.split()[0][:8]
    
    def get_fingerprint(self):
        return self._fingerprint
    
    def sign_message(self, message):
        result = subprocess.run(
            ['openssl', 'dgst', '-sha256', '-sign', str(self.private_key_path)],
            input=message.encode(),
            capture_output=True,
            check=True
        )
        return result.stdout.hex()
    
    def verify_signature(self, message, signature):
        """Verify a message signature using the public key"""
        try:
            # Create a temporary file for the signature (openssl expects binary file)
            sig_file = self.keys_dir / 'temp.sig'
            sig_file.write_bytes(bytes.fromhex(signature))
            
            # Verify signature
            result = subprocess.run(
                ['openssl', 'dgst', '-sha256', '-verify', str(self.public_key_path),
                 '-signature', str(sig_file)],
                input=message.encode(),
                capture_output=True
            )
            
            # Clean up temp file
            sig_file.unlink()
            
            return result.returncode == 0
        except Exception as e:
            app.logger.error(f"Signature verification failed: {str(e)}")
            return False

def async_task(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        thread = threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapped

class GitManager:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self._ensure_git_setup()
    
    def _ensure_git_setup(self):
        git_dir = self.repo_path / '.git'
        if not git_dir.exists():
            raise RuntimeError("Not a git repository. Please initialize git first.")
            
        # Verify git configuration exists
        try:
            subprocess.run(['git', 'config', 'user.name'], 
                         cwd=str(self.repo_path), 
                         check=True,
                         capture_output=True)
            subprocess.run(['git', 'config', 'user.email'], 
                         cwd=str(self.repo_path), 
                         check=True,
                         capture_output=True)
        except subprocess.CalledProcessError:
            raise RuntimeError("Git user.name or user.email not configured")
    
    @async_task
    def push_message(self, message_file):
        """Push a new message file to GitHub asynchronously"""
        try:
            # Stage the new file
            subprocess.run(['git', 'add', str(message_file)], 
                         cwd=str(self.repo_path), 
                         check=True)
            
            # Create commit
            commit_msg = f"Add message {message_file.name}"
            subprocess.run(['git', 'commit', '-m', commit_msg], 
                         cwd=str(self.repo_path), 
                         check=True)
            
            # Push to remote
            subprocess.run(['git', 'push'], 
                         cwd=str(self.repo_path), 
                         check=True)
            
            app.logger.info(f"Successfully pushed message {message_file.name} to GitHub")
        except subprocess.CalledProcessError as e:
            app.logger.error(f"Failed to push message {message_file.name} to GitHub: {str(e)}")

class MessageManager:
    def __init__(self, messages_dir, key_manager, git_manager=None):
        self.messages_dir = Path(messages_dir)
        self.messages_dir.mkdir(exist_ok=True)
        self.key_manager = key_manager
        self.git_manager = git_manager
    
    def sanitize_content(self, content):
        # Basic content sanitization
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string")
        
        # Remove null bytes and other control characters except newlines
        content = ''.join(char for char in content if char >= ' ' or char == '\n')
        
        # Limit message length (100KB)
        if len(content.encode('utf-8')) > 100 * 1024:
            raise ValueError("Message too long (maximum 100KB)")
            
        return content.strip()

    def save_message(self, content, type='message'):
        # Validate message type
        if type not in ['message', 'system', 'error']:
            raise ValueError("Invalid message type")
            
        # Sanitize content
        content = self.sanitize_content(content)
        
        now = datetime.now()
        timestamp = now.isoformat()
        filename = now.strftime("%Y%m%d_%H%M%S.txt")
        signature = self.key_manager.sign_message(content)
        fingerprint = self.key_manager.get_fingerprint()
        
        message = f"""Date: {timestamp}
Type: {type}
Fingerprint: {fingerprint}
Signature: {signature}

{content}"""
        
        message_file = self.messages_dir / filename
        message_file.write_text(message)
        
        # Push to GitHub if git manager is configured
        if self.git_manager:
            self.git_manager.push_message(message_file)
        
        return filename
    
    def get_messages(self):
        messages = []
        for file in self.messages_dir.glob("*.txt"):
            try:
                content = file.read_text().split("\n")
                message = {}
                
                # Parse headers
                i = 0
                message_content = []
                while i < len(content) and content[i]:
                    if ":" in content[i]:
                        key, value = content[i].split(":", 1)
                        message[key.lower().strip()] = value.strip()
                    i += 1
                
                # Get message content (strip to remove any trailing whitespace)
                message_content = "\n".join(content[i+1:]).strip()
                message['content'] = message_content
                
                messages.append(message)
            except Exception as e:
                app.logger.error(f"Error processing message {file.name}: {str(e)}")
                continue
        
        # Sort messages by actual timestamp instead of filename
        return sorted(messages, key=lambda x: x['date'])

# Initialize managers
key_manager = KeyManager(app.root_path + '/keys')
git_manager = None

# Only initialize git manager if we're in a git repository
try:
    git_manager = GitManager(app.root_path)
    app.logger.info("Git integration enabled")
except RuntimeError as e:
    app.logger.warning(f"Git integration disabled: {str(e)}")

message_manager = MessageManager(app.root_path + '/messages', key_manager, git_manager)

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'status': 'error',
        'message': 'The requested endpoint was not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'An internal server error occurred'
    }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        messages = message_manager.get_messages()
        return jsonify(messages)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/messages', methods=['POST'])
def post_message():
    try:
        # Handle both JSON and form-data
        if request.is_json:
            data = request.get_json()
            if not data:
                raise ValueError("Invalid JSON format")
        else:
            data = {'content': request.form.get('content'), 'type': 'message'}
        
        if not data or 'content' not in data:
            raise ValueError("Content is required")
            
        if not isinstance(data['content'], str):
            raise ValueError("Content must be a string")
            
        msg_type = data.get('type', 'message')
        filename = message_manager.save_message(data['content'], msg_type)
        
        return jsonify({
            'status': 'success',
            'id': filename
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        app.logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while processing your message'
        }), 500

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True)
