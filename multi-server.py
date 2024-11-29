from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import paramiko

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Example server details (replace with your actual servers)
SERVERS = [
    {'name': 'Server 1', 'host': 'yourserverip', 'username': 'root', 'password': 'serverpass'},
    {'name': 'Server 2', 'host': 'yourserverip', 'username': 'root', 'password': 'serverpass'},
    {'name': 'Server 3', 'host': 'yourserverip', 'username': 'root', 'password': 'serverpass'}
]

# Dummy user data for demonstration (replace with a real authentication method)
USER_CREDENTIALS = {
    'username': 'admin',
    'password': 'password123'  # Never hardcode passwords in a real app
}


# Function to execute shell commands over SSH
def execute_ssh_command(host, username, password, command):
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add host key (for simplicity)

        # Connect to the server
        ssh.connect(host, username=username, password=password)

        # Execute the command
        stdin, stdout, stderr = ssh.exec_command(command)

        # Read the output
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()

        # Close the connection
        ssh.close()

        if error:
            return error
        return output
    except Exception as e:
        return str(e)


# Function to get iptables rules from a remote server
def get_iptables_rules(host, username, password):
    command = "sudo iptables -S"
    return execute_ssh_command(host, username, password, command)



# Function to add a rule on a remote server
def add_iptables_rule(host, username, password, rule):
    command = f"sudo iptables {rule}"
    return execute_ssh_command(host, username, password, command)


# Function to delete a rule on a remote server
def delete_iptables_rule(host, username, password, rule):
    if rule.startswith('-A'):
        rule_to_delete = rule.replace('-A', '-D', 1)  # Replace only the first '-A' with '-D'
    else:
        rule_to_delete = f"-D {rule}"
    command = f"sudo iptables {rule_to_delete}"
    return execute_ssh_command(host, username, password, command)


# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('index'))  # Redirect to the main page if already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == USER_CREDENTIALS['username'] and password == USER_CREDENTIALS['password']:
            session['logged_in'] = True
            return redirect(url_for('index'))  # Redirect to the main page on successful login
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


# Route to the main page (only accessible if logged in)
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    return render_template('index.html', servers=SERVERS)


# Route to log out
@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Remove the login session
    return redirect(url_for('login'))


@app.route('/connect/<server_name>', methods=['GET'])
def connect_to_server(server_name):
    if 'logged_in' not in session:
        return jsonify({"message": "Unauthorized"}), 403  # Return unauthorized if not logged in

    server = next((s for s in SERVERS if s['name'] == server_name), None)
    if not server:
        return jsonify({"message": "Server not found"}), 404

    # Simulate SSH connection and fetching rules
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server['host'], username=server['username'], password=server['password'])

        # Get the current iptables rules from the server
        stdin, stdout, stderr = client.exec_command("sudo iptables -S")
        rules = stdout.read().decode().strip()
        client.close()

        return jsonify({"rules": rules})

    except Exception as e:
        return jsonify({"message": f"Error connecting to server: {str(e)}"}), 500


@app.route('/rules/<server_name>', methods=['POST'])
def manage_rules(server_name):
    if 'logged_in' not in session:
        return jsonify({"message": "Unauthorized"}), 403  # Return unauthorized if not logged in

    # Find the server details
    server = next((s for s in SERVERS if s['name'] == server_name), None)
    if not server:
        return jsonify({"message": "Server not found"}), 404

    # Get the rule and action from the request
    data = request.json
    action = data.get('action')
    rule = data.get('rule')

    # Handle SSH connection
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server['host'], username=server['username'], password=server['password'])

        # Fetch rules
        if action == 'fetch':
            stdin, stdout, stderr = client.exec_command("sudo iptables -S")
            rules = stdout.read().decode().splitlines()
            client.close()
            return jsonify({"rules": rules}), 200

        # Add rule
        if action == 'add':
            stdin, stdout, stderr = client.exec_command(f"iptables {rule}")
            client.close()
            return jsonify({"message": f"Successfully added rule: {rule}"}), 200

        # Delete rule
        elif action == 'delete':
            if rule.startswith('-A'):
                stdin, stdout, stderr = client.exec_command(f"iptables -D {rule[2:]}")
                client.close()
                return jsonify({"message": f"Successfully deleted rule: {rule}"}), 200
            else:
                return jsonify({"message": "Rule does not start with '-A', cannot delete"}), 400

        # Edit rule (delete old, add new)
        elif action == 'edit':
            old_rule, new_rule = rule.split(" -> ")
            if old_rule.startswith('-A'):
                stdin, stdout, stderr = client.exec_command(f"iptables -D {old_rule[2:]}")
                stdin, stdout, stderr = client.exec_command(f"iptables -A {new_rule[2:]}")
                client.close()
                return jsonify({"message": f"Successfully edited rule: {old_rule} -> {new_rule}"}), 200
            else:
                return jsonify({"message": "Old rule does not start with '-A', cannot edit"}), 400

        elif action == 'save_and_restart':
            stdin, stdout, stderr = client.exec_command(f"iptables-save > /etc/iptables/rules.v4 && systemctl restart iptables")
            client.close()
            return jsonify({"message": f"Successfully added rule: {rule}"}), 200

        return jsonify({'error': 'Unknown action'}), 400

    except Exception as e:
        return jsonify({"message": f"Error connecting to server or applying iptables rule: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
