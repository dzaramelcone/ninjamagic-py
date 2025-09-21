# Server Setup

Install uv, git, postgresql, fail2ban, ghostty.

Add users ninjamagic, ghdeploy, dzara as sudo.
Generate ssh keys for ghdeploy and dzara
Add ssh key.pub for dzara to /home/dzara/.ssh/authorized_keys

Setup a gh action to ssh into the ghdeploy user of the server (deploy.yml)
Add known hosts (via ssh-keyscan YOUR_SERVER_IP), private key and server to the github repo for the github action. See the deploy.yml for details.
Generate an ssh key to ninjamagic and add to gh repo's ACL so it can git clone.

TODO: We will need https. Once we have domain and a cert from a CA, setup nginx and have uvicorn host on 127.0.0.1.

# visudo
ghdeploy ALL=(root) NOPASSWD: /usr/bin/touch /var/lib/ninjamagic/deploy.trigger
ninjamagic ALL=(root) NOPASSWD: /bin/systemctl restart ninjamagic.service

# ufw 
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 8000/tcp

Remove the last one once nginx is up and force https.

# Enable the firewall
sudo ufw enable

# sshd
sudo nano /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers dzara ghdeploy

## postgresql

sudo -u postgres psql
CREATE DATABASE ninjamagic;
CREATE USER ninjamagic WITH ENCRYPTED PASSWORD 'a-very-strong-password';
GRANT ALL PRIVILEGES ON DATABASE ninjamagic TO ninjamagic;

Finally, be sure to run sqlc/schema.sql

TODO: setup alembic..

## nano /etc/systemd/system/ninjamagic.service
```
[Unit]
Description=ninjamagic
After=network.target postgresql.service

[Service]
User=ninjamagic
Group=ninjamagic
WorkingDirectory=/srv/ninjamagic-py
ExecStart=/snap/bin/uv run uvicorn ninjamagic.main:app --host=0.0.0.0 --ws-max-size=1024 --timeout-keep-alive=10 --h11-max-incomplete-event-size=4096
Restart=always
RestartSec=2
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target
```
sudo systemctl enable --now ninjamagic.service

## nano /etc/systemd/system/ninjamagic-deploy.path
```
[Unit]
Description=Watch deploy trigger for ninjamagic

[Path]
PathChanged=/var/lib/ninjamagic/deploy.trigger
Unit=ninjamagic-deploy.service

[Install]
WantedBy=multi-user.target
```
sudo systemctl enable --now ninjamagic-deploy.path

## nano /etc/systemd/system/ninjamagic-deploy.service
```
[Unit]
Description=Deploy ninjamagic

[Service]
Type=oneshot
User=ninjamagic
Group=ninjamagic
ExecStart=/usr/local/bin/ninjamagic-update.sh
```


### nano /home/ghdeploy/.ssh/authorized_keys
Replace with pub key generated:
```
command="sudo /usr/bin/touch /var/lib/ninjamagic/deploy.trigger",no-port-forwarding,no-x11-forwarding,no-agent-forwarding,no-pty {PUB KEY}
```


## nano /usr/local/bin/ninjamagic-update.sh
```
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/ninjamagic-py"
LOCK="/var/lock/ninjamagic-update.lock"

exec 9> "$LOCK"
flock -n 9 || { echo "[update] already running, skipping"; exit 0; }

cd "$APP_DIR"

# fetch & fast-forward to origin/main if changed
git fetch --quiet origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

[[ "$LOCAL" == "$REMOTE" ]] && { echo "[update] no change"; exit 0; }

echo "[update] $LOCAL -> $REMOTE"
git merge --ff-only origin/main
uv sync

sudo /bin/systemctl restart ninjamagic.service
```
sudo chown ninjamagic:ninjamagic /usr/local/bin/ninjamagic-update.sh
sudo chmod 550 /usr/local/bin/ninjamagic-update.sh


# Useful commands
journalctl -u ninjamagic -f
systemctl status ninjamagic
systemctl status postgresql
systemctl status fail2ban

## Check deploy trigger is working
sudo journalctl -u ninjamagic-deploy --no-pager

## Check auth logs
Make sure noone is brute forcing you.

# Fail2ban
`sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local`
Then enable ssh and incremental ban timers
