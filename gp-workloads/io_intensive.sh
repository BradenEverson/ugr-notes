#!/bin/bash
# I/O intensive workloads for syscall tracing
# These focus on disk operations, file system interactions, and I/O patterns

echo "Starting I/O intensive workload tests..."

echo "Running system call tracer..."
sudo killall python3
sudo rm -f out/io_intensive*.csv
sudo python3 tracer_rt.py -o out/io_intensive.csv -b 1024 &
TRACER_PID=$!
sleep 15

# Setup test directory
TEST_DIR="/tmp/io_test"
mkdir -p $TEST_DIR

# Sequential Write Operations
echo "=== Test 1: Large sequential write (buffered) ==="
sudo chrt -f 50 dd if=/dev/zero of=$TEST_DIR/seq_write.dat bs=1M count=500 oflag=sync
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 2: Large sequential write (direct I/O) ==="
sudo chrt -f 50 dd if=/dev/zero of=$TEST_DIR/direct_write.dat bs=1M count=500 oflag=direct
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 3: Small sequential writes (many syscalls) ==="
sudo chrt -f 50 dd if=/dev/zero of=$TEST_DIR/small_writes.dat bs=4K count=10000
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Sequential Read Operations
echo "=== Test 4: Large sequential read (buffered) ==="
sudo chrt -f 50 dd if=$TEST_DIR/seq_write.dat of=/dev/null bs=1M
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 5: Large sequential read (direct I/O) ==="
sudo chrt -f 50 dd if=$TEST_DIR/direct_write.dat of=/dev/null bs=1M iflag=direct
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 6: Small sequential reads ==="
sudo chrt -f 50 dd if=$TEST_DIR/small_writes.dat of=/dev/null bs=4K
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Random I/O patterns (if available)
echo "=== Test 7: Creating many small files ==="
sudo chrt -f 50 bash -c "for i in {1..1000}; do echo 'data' > $TEST_DIR/small_\$i.txt; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 8: Reading many small files ==="
sudo chrt -f 50 bash -c "for i in {1..1000}; do cat $TEST_DIR/small_\$i.txt > /dev/null; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 9: Stat operations on many files ==="
sudo chrt -f 50 bash -c "for i in {1..1000}; do stat $TEST_DIR/small_\$i.txt > /dev/null 2>&1; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 10: Directory listing (readdir intensive) ==="
sudo chrt -f 50 ls -la $TEST_DIR
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 11: Recursive directory traversal ==="
sudo chrt -f 50 find $TEST_DIR -type f
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# File metadata operations
echo "=== Test 12: Mass file rename ==="
sudo chrt -f 50 bash -c "for i in {1..500}; do mv $TEST_DIR/small_\$i.txt $TEST_DIR/renamed_\$i.txt 2>/dev/null; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 13: Mass file deletion ==="
sudo chrt -f 50 bash -c "for i in {1..500}; do rm $TEST_DIR/renamed_\$i.txt 2>/dev/null; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Copy operations
echo "=== Test 14: Large file copy ==="
sudo chrt -f 50 cp $TEST_DIR/seq_write.dat $TEST_DIR/copy_of_seq.dat
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 15: Rsync operation ==="
if command -v rsync &> /dev/null; then
    sudo chrt -f 50 rsync -a $TEST_DIR/seq_write.dat $TEST_DIR/rsync_copy.dat
    sleep 1
    sudo kill -USR1 $TRACER_PID
else
    echo "rsync not installed, skipping"
fi
sleep 1

# Sync operations (flush to disk)
echo "=== Test 16: Explicit sync operation ==="
sudo chrt -f 50 sync
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

echo "=== Test 17: Fsync operation ==="
sudo chrt -f 50 bash -c "dd if=/dev/zero of=$TEST_DIR/fsync_test.dat bs=1M count=100 conv=fsync"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Memory-mapped I/O
echo "=== Test 18: Memory-mapped file access ==="
sudo chrt -f 50 bash -c "cat $TEST_DIR/seq_write.dat > /dev/null"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Buffered vs unbuffered I/O comparison
echo "=== Test 19: Multiple concurrent writes ==="
sudo chrt -f 50 bash -c "
  dd if=/dev/zero of=$TEST_DIR/concurrent1.dat bs=1M count=100 &
  dd if=/dev/zero of=$TEST_DIR/concurrent2.dat bs=1M count=100 &
  dd if=/dev/zero of=$TEST_DIR/concurrent3.dat bs=1M count=100 &
  wait
"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Append operations
echo "=== Test 20: Append operations ==="
sudo chrt -f 50 bash -c "for i in {1..1000}; do echo 'line \$i' >> $TEST_DIR/append_test.txt; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Sparse file creation
echo "=== Test 21: Sparse file creation ==="
sudo chrt -f 50 dd if=/dev/zero of=$TEST_DIR/sparse.dat bs=1M seek=1000 count=1
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# File truncation
echo "=== Test 22: File truncation ==="
sudo chrt -f 50 truncate -s 100M $TEST_DIR/truncated.dat
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Directory operations
echo "=== Test 23: Directory creation and removal ==="
sudo chrt -f 50 bash -c "
  for i in {1..100}; do
    mkdir -p $TEST_DIR/subdir_\$i
  done
  for i in {1..100}; do
    rmdir $TEST_DIR/subdir_\$i
  done
"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# File locking
echo "=== Test 24: File locking operations ==="
sudo chrt -f 50 bash -c "
  exec 9>$TEST_DIR/lockfile
  flock 9
  echo 'locked' > $TEST_DIR/lockfile
  flock -u 9
"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Hard and symbolic links
echo "=== Test 25: Link creation ==="
sudo chrt -f 50 ln $TEST_DIR/seq_write.dat $TEST_DIR/hardlink.dat
sudo chrt -f 50 ln -s $TEST_DIR/seq_write.dat $TEST_DIR/symlink.dat
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# Extended attributes (if supported)
echo "=== Test 26: Extended attributes ==="
if command -v setfattr &> /dev/null; then
    sudo chrt -f 50 setfattr -n user.test -v "test_value" $TEST_DIR/seq_write.dat 2>/dev/null
    sudo chrt -f 50 getfattr -n user.test $TEST_DIR/seq_write.dat 2>/dev/null
    sleep 1
    sudo kill -USR1 $TRACER_PID
else
    echo "Extended attributes not available, skipping"
fi
sleep 1

# Inotify-style monitoring (simulate with stat)
echo "=== Test 27: Repeated stat checks (monitoring simulation) ==="
sudo chrt -f 50 bash -c "for i in {1..100}; do stat $TEST_DIR/seq_write.dat > /dev/null; done"
sleep 1
sudo kill -USR1 $TRACER_PID
sleep 1

# File permissions changes
echo "=== Test 28: Permission changes ==="
sudo chrt -f 50 bash -c "
  for i in {501..600}; do
    touch $TEST_DIR/small_\$i.txt
    chmod 644 $TEST_DIR/small_\$i.txt
    chmod 600 $TEST_DIR/small_\$i.txt
  done
"
sleep 1
sudo kill $TRACER_PID
sleep 1

# Cleanup
sudo killall python3
echo ""
echo "=== Cleanup ==="
rm -rf $TEST_DIR
echo ""
echo "All I/O intensive tests completed!"
