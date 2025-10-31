#!/bin/bash
# Syscall tracing test script for realtime processes
# Run these commands while the eBPF tracer is running

echo "Starting syscall tracing tests..."
echo "Make sure the eBPF tracer is running in another terminal!"
echo ""
sleep 2

# File Operations
echo "=== Test 1: Directory listing ==="
sudo chrt -f 50 ls -la /home
sleep 10

echo "=== Test 2: File reading ==="
sudo chrt -f 50 cat /etc/passwd
sleep 10

echo "=== Test 3: File copying ==="
sudo chrt -f 50 cp /etc/hosts /tmp/hosts_copy
sleep 10

echo "=== Test 4: File searching ==="
sudo chrt -f 50 find /usr/bin -name "python*"
sleep 10

echo "=== Test 5: Disk usage ==="
sudo chrt -f 50 du -sh /var/log
sleep 10

# Text Processing
echo "=== Test 6: Grep search ==="
sudo chrt -f 50 grep "root" /etc/passwd
sleep 10

echo "=== Test 7: Text editing ==="
echo "test content" > /tmp/test.txt
sudo chrt -f 50 sed 's/test/demo/g' /tmp/test.txt
sleep 10

echo "=== Test 8: Word counting ==="
sudo chrt -f 50 wc -l /etc/passwd
sleep 10

# Network Operations
echo "=== Test 9: DNS lookup ==="
sudo chrt -f 50 nslookup google.com
sleep 10

echo "=== Test 10: Ping ==="
sudo chrt -f 50 ping -c 3 8.8.8.8
sleep 10

echo "=== Test 11: Download ==="
sudo chrt -f 50 curl -o /tmp/page.html https://example.com
sleep 10

# System Information
echo "=== Test 12: Process listing ==="
sudo chrt -f 50 ps aux | head -20
sleep 10

echo "=== Test 13: System stats ==="
sudo chrt -f 50 uptime
sleep 10

echo "=== Test 14: Disk info ==="
sudo chrt -f 50 df -h
sleep 10

# Compression
echo "=== Test 15: Archive creation ==="
sudo chrt -f 50 tar -czf /tmp/test.tar.gz /etc/hosts
sleep 10

echo ""
echo "All tests completed!"
echo "Check your eBPF tracer output for syscall data"
