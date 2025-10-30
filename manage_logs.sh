#!/bin/bash
#
# Log management utility for Claude Agent API Server
#
# Usage:
#   ./manage_logs.sh list       - List all log files
#   ./manage_logs.sh latest     - Show latest log file
#   ./manage_logs.sh tail       - Tail latest log file
#   ./manage_logs.sh clean      - Clean old log files (keep last 10)
#   ./manage_logs.sh size       - Show total logs size

LOGS_DIR="logs"

case "$1" in
    list)
        echo "=== Log Files ==="
        if [ -d "$LOGS_DIR" ]; then
            ls -lht "$LOGS_DIR"/*.log 2>/dev/null | head -20
            echo ""
            echo "Total log files: $(ls "$LOGS_DIR"/*.log 2>/dev/null | wc -l)"
        else
            echo "No logs directory found"
        fi
        ;;

    latest)
        if [ -d "$LOGS_DIR" ]; then
            LATEST=$(ls -t "$LOGS_DIR"/*.log 2>/dev/null | head -1)
            if [ -n "$LATEST" ]; then
                echo "=== Latest log file: $LATEST ==="
                echo ""
                cat "$LATEST"
            else
                echo "No log files found"
            fi
        else
            echo "No logs directory found"
        fi
        ;;

    tail)
        if [ -d "$LOGS_DIR" ]; then
            LATEST=$(ls -t "$LOGS_DIR"/*.log 2>/dev/null | head -1)
            if [ -n "$LATEST" ]; then
                echo "=== Tailing latest log: $LATEST ==="
                echo "Press Ctrl+C to stop"
                echo ""
                tail -f "$LATEST"
            else
                echo "No log files found"
            fi
        else
            echo "No logs directory found"
        fi
        ;;

    clean)
        if [ -d "$LOGS_DIR" ]; then
            TOTAL=$(ls "$LOGS_DIR"/*.log 2>/dev/null | wc -l)
            if [ "$TOTAL" -gt 10 ]; then
                echo "=== Cleaning old log files (keeping last 10) ==="
                TO_DELETE=$((TOTAL - 10))
                ls -t "$LOGS_DIR"/*.log | tail -n "$TO_DELETE" | while read file; do
                    echo "Deleting: $file"
                    rm "$file"
                done
                echo "Deleted $TO_DELETE log files"
            else
                echo "Only $TOTAL log files found (keeping all)"
            fi
        else
            echo "No logs directory found"
        fi
        ;;

    size)
        if [ -d "$LOGS_DIR" ]; then
            echo "=== Logs Directory Size ==="
            du -sh "$LOGS_DIR"
            echo ""
            echo "=== Individual Log Files ==="
            du -h "$LOGS_DIR"/*.log 2>/dev/null | sort -rh | head -10
        else
            echo "No logs directory found"
        fi
        ;;

    *)
        echo "Log Management Utility"
        echo ""
        echo "Usage: $0 {list|latest|tail|clean|size}"
        echo ""
        echo "Commands:"
        echo "  list    - List all log files with details"
        echo "  latest  - Display the latest log file"
        echo "  tail    - Tail -f the latest log file"
        echo "  clean   - Clean old log files (keep last 10)"
        echo "  size    - Show logs directory size"
        exit 1
        ;;
esac
