#!/bin/bash
# Syscall tracing test script for realtime processes
# Run these commands while the eBPF tracer is running

echo "Starting syscall tracing tests..."

echo "Running system call tracer..."
sudo killall python3
sudo rm -f out/task_tests*.csv
sudo python3 tracer_rt.py -o out/task_tests.csv &
TRACER_PID=$!
sleep 20

# File Operations
echo "=== Test 1: Directory listing ==="
sudo chrt -f 50 ls -la /home
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 2: File reading ==="
sudo chrt -f 50 cat /etc/passwd
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 3: File copying ==="
sudo chrt -f 50 cp /etc/hosts /tmp/hosts_copy
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 4: File searching ==="
sudo chrt -f 50 find /usr/bin -name "python*"
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 5: Disk usage ==="
sudo chrt -f 50 du -sh /var/log
sudo kill -USR1 $TRACER_PID
sleep 1

# Text Processing
echo "=== Test 6: Grep search ==="
sudo chrt -f 50 grep "root" /etc/passwd
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 7: Text editing ==="
echo "test content" > /tmp/test.txt
sudo chrt -f 50 sed 's/test/demo/g' /tmp/test.txt
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 8: Word counting ==="
sudo chrt -f 50 wc -l /etc/passwd
sudo kill -USR1 $TRACER_PID
sleep 1

# Network Operations
echo "=== Test 9: DNS lookup ==="
sudo chrt -f 50 nslookup google.com
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 10: Ping ==="
sudo chrt -f 50 ping -c 3 8.8.8.8
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 11: Download ==="
sudo chrt -f 50 curl -o /tmp/page.html https://example.com
sudo kill -USR1 $TRACER_PID
sleep 1

# System Information
echo "=== Test 12: Process listing ==="
sudo chrt -f 50 ps aux | head -20
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 13: System stats ==="
sudo chrt -f 50 uptime
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 14: Disk info ==="
sudo chrt -f 50 df -h
sudo kill -USR1 $TRACER_PID
sleep 1

# Compression
echo "=== Test 15: Archive creation ==="
sudo chrt -f 50 tar -czf /tmp/test.tar.gz /etc/hosts
sudo kill $TRACER_PID
sleep 1

# Cleanup
sudo killall python3
echo ""
echo "=== Cleanup ==="
sudo rm -f /tmp/test.tar.gz
sudo rm -f /tmp/hosts_copy
sudo rm -f /tmp/test.txt
sudo rm -f /tmp/page.html
echo ""
echo "All tests completed!"
