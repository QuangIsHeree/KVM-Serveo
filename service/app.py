
# Make sure to get a self-signed ssl cert.
#
# Run this command!
# openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout cert.key -out cert.pem
#
# It will make the Selfsigned cert
#
# By default KVM-Serveo is on port 443
#
# Default login:
# admin:password

from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import secrets
import subprocess
import signal

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

PORTS_FILE = 'ports.txt'
SERVEO_IP = '138.68.79.95'

USERNAME = 'admin'
PASSWORD = 'password'
LOCAL_IP = '0.0.0.0'
MODEL = 'M1'
RAM = '1GB'
CPU = 'Intel Atom'

if not os.path.exists(PORTS_FILE):
    open(PORTS_FILE, 'w').close()

def add_port(router_port, target_port, ip):
    try:
        proc = subprocess.Popen([
            "ssh", "-o", "StrictHostKeyChecking=no", "-f", "-N",
            "-R", f"{router_port}:{ip}:{target_port}",
            'serveo.net'
        ])
        with open(PORTS_FILE, 'a') as f:
            f.write(f"{router_port},{target_port},{ip},{proc.pid}\n")
        return True
    except Exception as e:
        print("Error adding port:", e)
        return False

def remove_port(router_port):
    try:
        updated_lines = []
        with open(PORTS_FILE, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split(',')
            if parts[0] == router_port:
                pid = int(parts[3])
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception as e:
                    print(f"Failed to kill process {pid}: {e}")
            else:
                updated_lines.append(line)

        with open(PORTS_FILE, 'w') as f:
            f.writelines(updated_lines)

        return True
    except Exception as e:
        print("Error removing port:", e)
        return False

def read_ports():
    with open(PORTS_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def format_ports(ports):
    return [
        f"{p.split(',')[2]}:{p.split(',')[1]} <- Router -> http://{SERVEO_IP}:{p.split(',')[0]}"
        for p in ports
    ]

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('info_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/info_dashboard')
def info_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    ports = read_ports()
    return render_template('info_dashboard.html',
                           ports_count=len(ports),
                           ip=LOCAL_IP,
                           model=MODEL,
                           firmware="1.0-RELEASE",
                           cpu=CPU,
                           memory=RAM)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    ports = format_ports(read_ports())[::-1]
    return render_template('dashboard.html', ports=ports)

@app.route('/add_port', methods=['GET', 'POST'])
def add_port_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        router_port = request.form['router_port']
        target_port = request.form['target_port']
        ip = request.form['ip']
        if router_port.isdigit() and target_port.isdigit() and ip:
            if add_port(router_port, target_port, ip):
                flash(f"Router Port {router_port} -> {ip}:{target_port} added successfully!", 'success')
                return redirect(url_for('info_dashboard'))
            else:
                flash(f"Failed to add port {router_port} -> {ip}:{target_port}", 'danger')
        else:
            flash("Invalid port numbers or IP", 'danger')

    return render_template('add_port.html')

@app.route('/remove_port', methods=['GET', 'POST'])
def remove_port_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        router_port = request.form['port']
        ports = [p.split(',')[0] for p in read_ports()]
        if router_port in ports:
            if remove_port(router_port):
                flash(f"Router Port {router_port} removed successfully!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f"Failed to remove Router Port {router_port}", 'danger')
        else:
            flash(f"Router Port {router_port} not found", 'danger')

    return render_template('remove_port.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            global PASSWORD
            PASSWORD = new_password
            flash('Password reset successfully!', 'success')
            return redirect(url_for('info_dashboard'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template('reset_password.html')

def start_all_ports():
    for line in read_ports():
        router_port, target_port, ip, _ = line.split(',')
        subprocess.Popen([
            "ssh", "-o", "StrictHostKeyChecking=no", "-f", "-N",
            "-R", f"{router_port}:{ip}:{target_port}",
            'serveo.net'
        ])

if __name__ == '__main__':
    start_all_ports()
    app.run(host='0.0.0.0', port=443, ssl_context=('cert.pem', 'cert.key'), debug=True)
