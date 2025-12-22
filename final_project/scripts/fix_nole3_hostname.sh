#!/bin/bash
# Script để fix hostname resolution trên Nole3

echo "Fixing hostname resolution on Nole3..."

# Kết nối SSH và fix /etc/hosts
ssh nole3@192.168.80.178 << 'EOFSSH'
# Kiểm tra /etc/hosts hiện tại
echo "Current /etc/hosts:"
grep "nole" /etc/hosts || echo "No nole entries found"

# Thêm hostname mapping nếu chưa có
if ! grep -q "192.168.80.178.*nole3" /etc/hosts; then
    echo ""
    echo "Adding hostname mappings..."
    sudo bash -c 'cat >> /etc/hosts << EOF
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
EOF'
    echo "✓ Hostname mappings added"
fi

# Verify
echo ""
echo "Updated /etc/hosts:"
grep "nole" /etc/hosts

# Test resolution
echo ""
echo "Testing hostname resolution:"
ping -c 1 nole3 && echo "✓ nole3 resolves correctly" || echo "❌ nole3 still fails"

# Stop HDFS
echo ""
echo "Stopping HDFS..."
~/hadoop/sbin/stop-dfs.sh 2>/dev/null || true
sleep 3

# Start HDFS
echo ""
echo "Starting HDFS..."
~/hadoop/sbin/start-dfs.sh
sleep 5

# Disable safe mode
echo ""
echo "Disabling safe mode..."
~/hadoop/bin/hdfs dfsadmin -safemode leave

# Check HDFS status
echo ""
echo "HDFS Status:"
~/hadoop/bin/hdfs dfsadmin -report | head -20
EOFSSH

echo ""
echo "Done! Check output above for any errors."
