#!/bin/bash
# CPU-intensive and long-running workload tests for syscall tracing
# Run these while the eBPF tracer is active

echo "Starting intensive workload tests..."
echo "These tests will take longer and generate more syscalls"
echo ""
sleep 2

# Compression/Decompression (I/O + CPU intensive)
echo "=== Test 1: Large file compression ==="
dd if=/dev/urandom of=/tmp/largefile bs=1M count=100 2>/dev/null
sudo chrt -f 50 gzip -c /tmp/largefile > /tmp/largefile.gz
sleep 10

echo "=== Test 2: Decompression ==="
sudo chrt -f 50 gunzip -c /tmp/largefile.gz > /tmp/largefile_uncompressed
sleep 10

# Cryptographic operations (CPU intensive)
echo "=== Test 3: SHA256 hashing ==="
sudo chrt -f 50 sha256sum /tmp/largefile
sleep 10

echo "=== Test 4: MD5 hashing ==="
sudo chrt -f 50 md5sum /tmp/largefile
sleep 10

# Text processing at scale
echo "=== Test 5: Large grep with regex ==="
sudo chrt -f 50 grep -r "^[a-z]*$" /usr/share/doc/ 2>/dev/null | head -1000
sleep 10

echo "=== Test 6: AWK processing ==="
sudo chrt -f 50 awk '{sum+=$1} END {print sum}' /proc/*/stat 2>/dev/null
sleep 10

# Compilation (CPU + I/O intensive)
echo "=== Test 7: C compilation ==="
cat > /tmp/test.c << 'EOF'
#include <stdio.h>
int main() {
    int sum = 0;
    for(int i = 0; i < 1000000; i++) {
        sum += i;
    }
    printf("Sum: %d\n", sum);
    return 0;
}
EOF
sudo chrt -f 50 gcc /tmp/test.c -o /tmp/test -O2
sleep 10

# Sorting (CPU + memory intensive)
echo "=== Test 8: Large sort operation ==="
seq 1 100000 | shuf > /tmp/numbers.txt
sudo chrt -f 50 sort -n /tmp/numbers.txt > /tmp/sorted.txt
sleep 10

# Image processing (if ImageMagick is available)
echo "=== Test 9: Image conversion (if available) ==="
if command -v convert &> /dev/null; then
    convert -size 2000x2000 xc:white /tmp/test.png 2>/dev/null
    sudo chrt -f 50 convert /tmp/test.png -resize 50% /tmp/test_small.png 2>/dev/null
else
    echo "ImageMagick not installed, skipping"
fi
sleep 10

# Database-like operations
echo "=== Test 10: SQLite operations ==="
cat > /tmp/test.sql << 'EOF'
CREATE TABLE test(id INTEGER, value TEXT);
INSERT INTO test VALUES (1, 'test1');
INSERT INTO test VALUES (2, 'test2');
SELECT * FROM test;
EOF
sudo chrt -f 50 sqlite3 /tmp/test.db < /tmp/test.sql 2>/dev/null
sleep 10

# CPU stress test (pure computation)
echo "=== Test 11: CPU intensive calculation ==="
sudo chrt -f 50 bash -c 'for i in {1..1000000}; do ((result=i*i)); done; echo "Done"'
sleep 10

# Python computation (if available)
echo "=== Test 12: Python computation ==="
if command -v python3 &> /dev/null; then
    sudo chrt -f 50 python3 -c "import time; sum(i**2 for i in range(1000000)); print('Done')"
else
    echo "Python3 not installed, skipping"
fi
sleep 10

# Parallel operations
echo "=== Test 13: Parallel file operations ==="
mkdir -p /tmp/testdir
sudo chrt -f 50 bash -c 'for i in {1..100}; do echo "test$i" > /tmp/testdir/file$i; done'
sudo chrt -f 50 find /tmp/testdir -type f -exec cat {} \; > /dev/null
sleep 10

# Archive extraction (I/O heavy)
echo "=== Test 14: Archive extraction ==="
sudo chrt -f 50 tar -xzf /tmp/test.tar.gz -C /tmp/ 2>/dev/null
sleep 10

# JSON parsing (if jq available)
echo "=== Test 15: JSON processing ==="
if command -v jq &> /dev/null; then
    echo '{"users":[{"name":"alice","age":30},{"name":"bob","age":25}]}' > /tmp/test.json
    for i in {1..1000}; do cat /tmp/test.json; done | sudo chrt -f 50 jq '.users[] | select(.age > 20)' > /dev/null
else
    echo "jq not installed, skipping"
fi
sleep 10

# Memory stress
echo "=== Test 16: Memory allocation test ==="
sudo chrt -f 50 bash -c 'array=(); for i in {1..100000}; do array+=($i); done; echo "Done"'
sleep 10

# Disk I/O test
echo "=== Test 17: Sequential disk write ==="
sudo chrt -f 50 dd if=/dev/zero of=/tmp/disktest bs=1M count=100 2>/dev/null
sleep 10

echo "=== Test 18: Sequential disk read ==="
sudo chrt -f 50 dd if=/tmp/disktest of=/dev/null bs=1M 2>/dev/null
sleep 10

# Cleanup
echo ""
echo "=== Cleanup ==="
rm -f /tmp/largefile /tmp/largefile.gz /tmp/largefile_uncompressed
rm -f /tmp/test.c /tmp/test /tmp/numbers.txt /tmp/sorted.txt
rm -f /tmp/test.png /tmp/test_small.png /tmp/test.db /tmp/test.sql
rm -f /tmp/test.json /tmp/disktest /tmp/page.html /tmp/hosts_copy
rm -rf /tmp/testdir
echo ""
echo "All intensive workload tests completed!"
echo "Check your eBPF tracer output for syscall patterns"
