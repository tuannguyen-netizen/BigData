# FIX RABBITMQ MANAGEMENT UI

## Vấn đề
- `telnet localhost 5672` thành công (RabbitMQ đang chạy)
- Nhưng không mở được http://localhost:15672 (Management UI)

## Nguyên nhân
Management plugin chưa được enable hoặc chưa start đúng cách.

## Giải pháp

### Bước 1: Kiểm tra RabbitMQ status
```bash
sudo systemctl status rabbitmq-server
```

### Bước 2: Enable Management Plugin
```bash
sudo rabbitmq-plugins enable rabbitmq_management
```

### Bước 3: Restart RabbitMQ
```bash
sudo systemctl restart rabbitmq-server
```

### Bước 4: Kiểm tra port 15672
```bash
# Kiểm tra port đang listen
sudo netstat -tulpn | grep 15672

# Hoặc dùng ss
sudo ss -tulpn | grep 15672

# Hoặc dùng lsof
sudo lsof -i :15672
```

### Bước 5: Kiểm tra firewall
```bash
# Kiểm tra firewall status
sudo ufw status

# Nếu firewall đang bật, allow port 15672
sudo ufw allow 15672/tcp
```

### Bước 6: Kiểm tra RabbitMQ logs
```bash
sudo tail -f /var/log/rabbitmq/rabbit@*.log
```

### Bước 7: Test lại
```bash
# Test từ localhost
curl http://localhost:15672

# Nếu thành công, sẽ thấy HTML response

# Test telnet
telnet localhost 15672
```

### Bước 8: Truy cập Web UI
```bash
# Từ browser trên cùng máy:
http://localhost:15672

# Từ máy khác (thay IP):
http://192.168.80.178:15672

# Login:
# Username: guest
# Password: guest
```

## Nếu vẫn không được

### Option 1: Reinstall RabbitMQ
```bash
# Stop service
sudo systemctl stop rabbitmq-server

# Remove
sudo apt-get remove --purge rabbitmq-server

# Clean
sudo rm -rf /var/lib/rabbitmq
sudo rm -rf /etc/rabbitmq

# Reinstall
sudo apt-get update
sudo apt-get install -y rabbitmq-server

# Enable management
sudo rabbitmq-plugins enable rabbitmq_management

# Start
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Check
sudo systemctl status rabbitmq-server
```

### Option 2: Kiểm tra binding address
```bash
# Check RabbitMQ config
sudo cat /etc/rabbitmq/rabbitmq.conf

# Nếu file không tồn tại, tạo mới:
sudo nano /etc/rabbitmq/rabbitmq.conf
```

Thêm nội dung:
```
# Allow management UI from all interfaces
management.tcp.port = 15672
management.tcp.ip = 0.0.0.0

# Allow AMQP from all interfaces  
listeners.tcp.default = 5672
```

Restart:
```bash
sudo systemctl restart rabbitmq-server
```

### Option 3: Kiểm tra user permissions
```bash
# List users
sudo rabbitmqctl list_users

# Nếu không có user guest, tạo mới:
sudo rabbitmqctl add_user guest guest
sudo rabbitmqctl set_user_tags guest administrator
sudo rabbitmqctl set_permissions -p / guest ".*" ".*" ".*"
```

## Verification

### 1. Check service
```bash
sudo systemctl status rabbitmq-server
# Phải thấy: active (running)
```

### 2. Check ports
```bash
sudo netstat -tulpn | grep beam
# Phải thấy:
# - Port 5672 (AMQP)
# - Port 15672 (Management UI)
# - Port 25672 (Clustering)
```

### 3. Check plugins
```bash
sudo rabbitmq-plugins list
# Phải thấy [E*] rabbitmq_management
```

### 4. Test Web UI
```bash
curl -u guest:guest http://localhost:15672/api/overview
# Phải trả về JSON response
```

### 5. Access from browser
- URL: http://localhost:15672 (hoặc http://192.168.80.178:15672)
- Username: guest
- Password: guest

## Nếu đang ở máy khác (không phải Nole3)

Bạn cần truy cập qua IP của Nole3:
```
http://192.168.80.178:15672
```

Nếu không mở được, kiểm tra:
1. Firewall trên Nole3
2. Network connectivity từ máy của bạn đến Nole3
3. RabbitMQ có bind đúng interface không

## Quick Fix Script

```bash
#!/bin/bash
# Quick fix RabbitMQ Management UI

echo "Stopping RabbitMQ..."
sudo systemctl stop rabbitmq-server

echo "Enabling management plugin..."
sudo rabbitmq-plugins enable rabbitmq_management

echo "Starting RabbitMQ..."
sudo systemctl start rabbitmq-server

echo "Waiting for RabbitMQ to start..."
sleep 5

echo "Checking status..."
sudo systemctl status rabbitmq-server

echo "Checking ports..."
sudo netstat -tulpn | grep beam

echo "Testing Management UI..."
curl -u guest:guest http://localhost:15672/api/overview

echo ""
echo "Done! Try accessing:"
echo "http://localhost:15672"
echo "Username: guest"
echo "Password: guest"
```

Lưu script và chạy:
```bash
chmod +x fix_rabbitmq.sh
./fix_rabbitmq.sh
```
