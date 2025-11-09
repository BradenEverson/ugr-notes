#!/bin/bash
# Mixed workloads combining CPU, I/O, and network operations
# These simulate real-world application patterns

echo "Starting mixed workload tests..."

echo "Running system call tracer..."
sudo rm -f out/mixed*.csv
sudo python3 tracer_rt.py -o out/mixed.csv &
TRACER_PID=$1
sleep 15

TEST_DIR="/tmp/mixed_test"
mkdir -p $TEST_DIR

# Web server simulation
echo "=== Test 1: Web server simulation (download + parse + save) ==="
sudo chrt -f 50 bash -c "
  curl -s https://example.com > $TEST_DIR/webpage.html
  grep -o 'href=\"[^\"]*\"' $TEST_DIR/webpage.html > $TEST_DIR/links.txt
  wc -l $TEST_DIR/links.txt
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Log processing pipeline
echo "=== Test 2: Log processing (read + parse + aggregate + write) ==="
sudo chrt -f 50 bash -c "
  # Generate fake log data
  for i in {1..10000}; do
    echo \"\$(date '+%Y-%m-%d %H:%M:%S') [INFO] Request from 192.168.1.\$((i % 255)) - Status: \$((200 + RANDOM % 100))\" >> $TEST_DIR/access.log
  done
  
  # Process logs
  grep 'Status: 200' $TEST_DIR/access.log | wc -l > $TEST_DIR/success_count.txt
  awk '{print \$6}' $TEST_DIR/access.log | sort | uniq -c > $TEST_DIR/ip_counts.txt
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Data ETL (Extract, Transform, Load)
echo "=== Test 3: ETL pipeline (download + transform + compress + save) ==="
sudo chrt -f 50 bash -c "
  # Extract: generate CSV data
  echo 'id,name,value' > $TEST_DIR/data.csv
  for i in {1..5000}; do
    echo \"\$i,user\$i,\$((RANDOM % 1000))\" >> $TEST_DIR/data.csv
  done
  
  # Transform: filter and aggregate
  awk -F',' '\$3 > 500 {sum+=\$3; count++} END {print \"Average:\", sum/count}' $TEST_DIR/data.csv > $TEST_DIR/summary.txt
  
  # Load: compress and save
  gzip -c $TEST_DIR/data.csv > $TEST_DIR/data.csv.gz
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Build and test workflow
echo "=== Test 4: Build workflow (compile + test + package) ==="
sudo chrt -f 50 bash -c "
  # Create source files
  cat > $TEST_DIR/main.c << 'EOF'
#include <stdio.h>
#include <math.h>
int calculate(int n) {
    int sum = 0;
    for(int i = 0; i < n; i++) {
        sum += (int)sqrt(i);
    }
    return sum;
}
int main() {
    printf(\"Result: %d\\n\", calculate(10000));
    return 0;
}
EOF
  
  # Compile
  gcc $TEST_DIR/main.c -o $TEST_DIR/app -lm -O2
  
  # Run and capture output
  $TEST_DIR/app > $TEST_DIR/output.txt
  
  # Package
  tar -czf $TEST_DIR/app.tar.gz -C $TEST_DIR app output.txt
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Image processing workflow
echo "=== Test 5: Image workflow (generate + process + analyze) ==="
if command -v convert &> /dev/null; then
  sudo chrt -f 50 bash -c "
    # Generate image
    convert -size 1000x1000 plasma: $TEST_DIR/image.png
    
    # Process: resize and convert
    convert $TEST_DIR/image.png -resize 500x500 $TEST_DIR/thumb.png
    convert $TEST_DIR/image.png -quality 80 $TEST_DIR/image.jpg
    
    # Analyze: get file info
    stat $TEST_DIR/image.png > $TEST_DIR/image_info.txt
    identify $TEST_DIR/image.png >> $TEST_DIR/image_info.txt
  "
  sudo kill -USR1 $TRACER_PID
else
  echo "ImageMagick not available, skipping"
fi
sleep 1

# Database-backed application
echo "=== Test 6: Database application (create + insert + query + backup) ==="
sudo chrt -f 50 bash -c "
  # Create and populate database
  sqlite3 $TEST_DIR/app.db << 'EOF'
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, score INTEGER);
CREATE INDEX idx_score ON users(score);
INSERT INTO users (name, score) 
  SELECT 'user' || value, abs(random() % 1000)
  FROM generate_series(1, 1000);
SELECT COUNT(*), AVG(score) FROM users WHERE score > 500;
EOF
  
  # Backup database
  sqlite3 $TEST_DIR/app.db '.dump' | gzip > $TEST_DIR/backup.sql.gz
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Data science workflow
echo "=== Test 7: Data analysis (generate + compute + visualize) ==="
if command -v python3 &> /dev/null; then
  sudo chrt -f 50 python3 << 'EOF'
import json
import math

# Generate data
data = [{"x": i, "y": math.sin(i/10) * 100 + i} for i in range(1000)]

# Compute statistics
avg = sum(d["y"] for d in data) / len(data)
max_val = max(d["y"] for d in data)
min_val = min(d["y"] for d in data)

# Save results
with open("/tmp/mixed_test/analysis.json", "w") as f:
    json.dump({
        "count": len(data),
        "average": avg,
        "max": max_val,
        "min": min_val
    }, f)

print(f"Processed {len(data)} points")
EOF
sudo kill -USR1 $TRACER_PID
else
  echo "Python3 not available, skipping"
fi
sleep 1

# API client simulation
echo "=== Test 8: API client (fetch + validate + cache + retry) ==="
sudo chrt -f 50 bash -c "
  # Fetch data
  curl -s https://api.github.com/zen > $TEST_DIR/api_response.txt 2>/dev/null || echo 'offline' > $TEST_DIR/api_response.txt
  
  # Validate (check non-empty)
  if [ -s $TEST_DIR/api_response.txt ]; then
    echo 'valid' > $TEST_DIR/validation.txt
  else
    echo 'invalid' > $TEST_DIR/validation.txt
  fi
  
  # Cache with timestamp
  echo \"\$(date +%s): \$(cat $TEST_DIR/api_response.txt)\" >> $TEST_DIR/cache.txt
"
sudo kill -USR1 $TRACER_PID
sleep 1

# File synchronization
echo "=== Test 9: File sync (compare + copy + verify) ==="
sudo chrt -f 50 bash -c "
  # Create source files
  mkdir -p $TEST_DIR/source $TEST_DIR/dest
  for i in {1..50}; do
    dd if=/dev/urandom of=$TEST_DIR/source/file\$i.dat bs=1K count=100 2>/dev/null
  done
  
  # Sync with checksum verification
  for file in $TEST_DIR/source/*; do
    filename=\$(basename \$file)
    cp \$file $TEST_DIR/dest/\$filename
    md5sum \$file >> $TEST_DIR/checksums.txt
  done
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Backup and restore workflow
echo "=== Test 10: Backup workflow (scan + compress + encrypt-sim + verify) ==="
sudo chrt -f 50 bash -c "
  # Scan directory tree
  find $TEST_DIR/source -type f > $TEST_DIR/file_list.txt
  
  # Compress
  tar -czf $TEST_DIR/backup.tar.gz -C $TEST_DIR source/
  
  # Simulate encryption (using base64 for demo)
  base64 $TEST_DIR/backup.tar.gz > $TEST_DIR/backup.tar.gz.enc
  
  # Verify archive
  tar -tzf $TEST_DIR/backup.tar.gz > $TEST_DIR/archive_contents.txt
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Monitoring/metrics collection
echo "=== Test 11: Metrics collection (sample + aggregate + store) ==="
sudo chrt -f 50 bash -c "
  # Collect system metrics
  for i in {1..10}; do
    echo \"\$(date +%s),\$(cat /proc/loadavg | awk '{print \$1}'),\$(df / | tail -1 | awk '{print \$5}')\" >> $TEST_DIR/metrics.csv
    sleep 0.1
  done
  
  # Aggregate
  awk -F',' '{sum+=\$2; count++} END {print \"Avg load:\", sum/count}' $TEST_DIR/metrics.csv > $TEST_DIR/metrics_summary.txt
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Message queue simulation
echo "=== Test 12: Message queue (produce + consume + process) ==="
sudo chrt -f 50 bash -c "
  # Producer: generate messages
  for i in {1..100}; do
    echo \"{\\\"id\\\": \$i, \\\"timestamp\\\": \$(date +%s), \\\"data\\\": \\\"message\$i\\\"}\" >> $TEST_DIR/queue.jsonl
  done
  
  # Consumer: process messages
  while IFS= read -r line; do
    echo \$line | grep -o '\"id\": [0-9]*' >> $TEST_DIR/processed_ids.txt
  done < $TEST_DIR/queue.jsonl
  
  # Cleanup queue
  > $TEST_DIR/queue.jsonl
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Batch processing job
echo "=== Test 13: Batch job (split + parallel process + merge) ==="
sudo chrt -f 50 bash -c "
  # Generate input
  seq 1 10000 > $TEST_DIR/input.txt
  
  # Split
  split -l 2500 $TEST_DIR/input.txt $TEST_DIR/chunk_
  
  # Process chunks (simulate parallel)
  for chunk in $TEST_DIR/chunk_*; do
    awk '{print \$1 * 2}' \$chunk > \${chunk}.out
  done
  
  # Merge results
  cat $TEST_DIR/chunk_*.out > $TEST_DIR/output.txt
  rm $TEST_DIR/chunk_*
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Configuration management
echo "=== Test 14: Config update (read + validate + backup + write) ==="
sudo chrt -f 50 bash -c "
  # Create config
  cat > $TEST_DIR/config.json << 'EOF'
{
  \"app_name\": \"test_app\",
  \"version\": \"1.0\",
  \"settings\": {
    \"timeout\": 30,
    \"retries\": 3
  }
}
EOF
  
  # Backup
  cp $TEST_DIR/config.json $TEST_DIR/config.json.bak
  
  # Validate (check valid JSON with python or jq)
  python3 -m json.tool $TEST_DIR/config.json > /dev/null 2>&1 && echo 'valid' > $TEST_DIR/config_status.txt
  
  # Update
  sed -i 's/\"1.0\"/\"1.1\"/' $TEST_DIR/config.json
"
sudo kill -USR1 $TRACER_PID
sleep 1

# Report generation
echo "=== Test 15: Report generation (collect + analyze + format + export) ==="
sudo chrt -f 50 bash -c "
  # Collect data from multiple sources
  df -h > $TEST_DIR/disk_report.txt
  free -h > $TEST_DIR/memory_report.txt
  uptime > $TEST_DIR/uptime_report.txt
  
  # Generate combined report
  cat > $TEST_DIR/system_report.html << 'EOF'
<html>
<head><title>System Report</title></head>
<body>
<h1>System Report</h1>
<h2>Disk Usage</h2>
<pre>DISK_DATA</pre>
<h2>Memory Usage</h2>
<pre>MEMORY_DATA</pre>
</body>
</html>
EOF
  
  # Replace placeholders (simple version)
  sed -i '/DISK_DATA/r $TEST_DIR/disk_report.txt' $TEST_DIR/system_report.html
  sed -i 's/DISK_DATA//' $TEST_DIR/system_report.html
"
sudo kill $TRACER_PID
sleep 1

# Cleanup
echo ""
echo "=== Cleanup ==="
sudo rm -rf $TEST_DIR
echo ""
echo "All mixed workload tests completed!"
