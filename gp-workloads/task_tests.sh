#!/bin/bash
# Syscall tracing test script for realtime processes
# Run these commands while the eBPF tracer is running

echo "Starting syscall tracing tests..."
echo "Make sure the eBPF tracer is running in another terminal!"
echo ""
sleep 2

# File Operations
echo "=== Test 1: Directory listing ==="
sudo python3 tracer_rt.py > dir_listing.txt &
TRACER_PID=$!
sudo chrt -f 50 ls -la /home
sudo kill $TRACER_PID
sleep 1

echo "=== Test 2: File reading ==="
sudo python3 tracer_rt.py > file_read.txt &
TRACER_PID=$!
sudo chrt -f 50 cat /etc/passwd
sudo kill $TRACER_PID
sleep 1

echo "=== Test 3: File copying ==="
sudo python3 tracer_rt.py > file_copy.txt &
TRACER_PID=$!
sudo chrt -f 50 cp /etc/hosts /tmp/hosts_copy
sudo kill $TRACER_PID
sleep 1

echo "=== Test 4: File searching ==="
sudo python3 tracer_rt.py > file_search.txt &
TRACER_PID=$!
sudo chrt -f 50 find /usr/bin -name "python*"
sudo kill $TRACER_PID
sleep 1

echo "=== Test 5: Disk usage ==="
sudo python3 tracer_rt.py > disk_usage.txt &
TRACER_PID=$!
sudo chrt -f 50 du -sh /var/log
sudo kill $TRACER_PID
sleep 1

# Text Processing
echo "=== Test 6: Grep search ==="
sudo python3 tracer_rt.py > grep_search.txt &
TRACER_PID=$!
sudo chrt -f 50 grep "root" /etc/passwd
sudo kill $TRACER_PID
sleep 1

echo "=== Test 7: Text editing ==="
sudo python3 tracer_rt.py > text_edit.txt &
TRACER_PID=$!
echo "test content" > /tmp/test.txt
sudo chrt -f 50 sed 's/test/demo/g' /tmp/test.txt
sudo kill $TRACER_PID
sleep 1

echo "=== Test 8: Word counting ==="
sudo python3 tracer_rt.py > word_count.txt &
TRACER_PID=$!
sudo chrt -f 50 wc -l /etc/passwd
sudo kill $TRACER_PID
sleep 1

# Network Operations
echo "=== Test 9: DNS lookup ==="
sudo python3 tracer_rt.py > dns_lookup.txt &
TRACER_PID=$!
sudo chrt -f 50 nslookup google.com
sudo kill $TRACER_PID
sleep 1

echo "=== Test 10: Ping ==="
sudo python3 tracer_rt.py > ping.txt &
TRACER_PID=$!
sudo chrt -f 50 ping -c 3 8.8.8.8
sudo kill $TRACER_PID
sleep 1

echo "=== Test 11: Download ==="
sudo python3 tracer_rt.py > download.txt &
TRACER_PID=$!
sudo chrt -f 50 curl -o /tmp/page.html https://example.com
sudo kill $TRACER_PID
sleep 1

# System Information
echo "=== Test 12: Process listing ==="
sudo python3 tracer_rt.py > process_listing.txt &
TRACER_PID=$!
sudo chrt -f 50 ps aux | head -20
sudo kill $TRACER_PID
sleep 1

echo "=== Test 13: System stats ==="
sudo python3 tracer_rt.py > system_stats.txt &
TRACER_PID=$!
sudo chrt -f 50 uptime
sudo kill $TRACER_PID
sleep 1

echo "=== Test 14: Disk info ==="
sudo python3 tracer_rt.py > disk_info.txt &
TRACER_PID=$!
sudo chrt -f 50 df -h
sudo kill $TRACER_PID
sleep 1

# Compression
echo "=== Test 15: Archive creation ==="
sudo python3 tracer_rt.py > archive_create.txt &
TRACER_PID=$!
sudo chrt -f 50 tar -czf /tmp/test.tar.gz /etc/hosts
sudo kill $TRACER_PID
sleep 1

echo ""
echo "All tests completed!"
echo "Check your eBPF tracer output for syscall data"
