#!/bin/bash

# Script to run main.py followed by frontend/generate_site.py in a virtual environment
# With optional web server functionality

# Initialize variables
SERVE_WEBSITE=false
PORT=8000
INTERVAL=0
SERVER_PID=""
SERVER_PGID=""
CLEANUP_EXIT_CODE=0

# Function to clean up background processes on exit
cleanup() {
    echo -e "\nCleaning up..."
    
    # Store the exit code reason if provided as an argument
    if [ -n "$1" ] && [ "$1" -eq "$1" ] 2>/dev/null; then
        CLEANUP_EXIT_CODE=$1
    fi
    
    # Kill the web server process group if it exists
    if [ -n "$SERVER_PGID" ]; then
        echo "Stopping web server process group (PGID: $SERVER_PGID)..."
        # Send termination signal to the entire process group
        pkill -TERM -g $SERVER_PGID 2>/dev/null
        
        # Wait briefly for processes to terminate gracefully
        for i in {1..5}; do
            if ! pkill -g $SERVER_PGID -0 2>/dev/null; then
                echo "Web server process group stopped successfully."
                break
            fi
            echo "Waiting for processes to terminate... ($i/5)"
            sleep 1
        done
        
        # Force kill if still running
        if pkill -g $SERVER_PGID -0 2>/dev/null; then
            echo "Web server processes did not terminate gracefully, forcing..."
            pkill -KILL -g $SERVER_PGID 2>/dev/null
            sleep 0.5
            
            # Verify all processes were killed
            if pkill -g $SERVER_PGID -0 2>/dev/null; then
                echo "WARNING: Some processes may still be running!" >&2
                ps -o pid,ppid,pgid,command -g $SERVER_PGID 2>/dev/null || true
            else
                echo "All processes in group terminated."
            fi
        fi
    elif [ -n "$SERVER_PID" ]; then
        # Fallback to old method if we only have PID but no PGID
        echo "Stopping web server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null
        
        # Wait briefly for process to terminate gracefully
        for i in {1..3}; do
            if ! kill -0 $SERVER_PID 2>/dev/null; then
                echo "Web server stopped successfully."
                break
            fi
            sleep 0.5
        done
        
        # Force kill if still running
        if kill -0 $SERVER_PID 2>/dev/null; then
            echo "Web server did not terminate gracefully, forcing..."
            kill -9 $SERVER_PID 2>/dev/null
        fi
    fi
    
    # Find and kill any remaining child processes from this script
    local my_pid=$$
    local my_pgid=$(ps -o pgid= -p $my_pid | tr -d ' ')
    
    # Kill all processes in our process group except ourselves
    if [ -n "$my_pgid" ]; then
        echo "Checking for remaining processes in our group (PGID: $my_pgid)..."
        # Get a list of PIDs in our process group except our own PID
        local group_pids=$(ps -o pid= -g $my_pgid | grep -v "^$my_pid$" | tr -d ' ')
        
        if [ -n "$group_pids" ]; then
            echo "Stopping remaining child processes..."
            # Try graceful termination
            kill $group_pids 2>/dev/null
            sleep 1
            
            # Force kill any stubborn processes
            for pid in $group_pids; do
                if kill -0 $pid 2>/dev/null; then
                    echo "Forcing termination of process $pid"
                    kill -9 $pid 2>/dev/null
                fi
            done
        else
            echo "No remaining child processes found."
        fi
    fi
    
    echo "Cleanup complete. Exiting..."
    exit $CLEANUP_EXIT_CODE
}

# Set up trap for clean exit
trap cleanup SIGINT SIGTERM SIGHUP

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -w|--web)
            SERVE_WEBSITE=true
            if [[ "$2" =~ ^[0-9]+$ ]] && [[ "$2" != -* ]]; then
                PORT="$2"
                shift
            fi
            ;;
        -i|--interval)
            if [[ "$2" =~ ^[0-9]+$ ]] && [[ "$2" != -* ]]; then
                INTERVAL="$2"
                shift
            else
                echo "ERROR: --interval requires a numeric value in minutes" >&2
                exit 1
            fi
            ;;
        --blast)
            echo "Blasting the database and website directory for a clean start..."
            # Delete the database file if it exists
            if [ -f "canvas.db" ]; then
                echo "Removing canvas.db..."
                rm -f "canvas.db"
                echo "Database file removed."
            else
                echo "Database file canvas.db not found (may already be clean)."
            fi
            
            # Delete the website directory if it exists
            if [ -d "frontend/website" ]; then
                echo "Removing frontend/website directory..."
                rm -rf "frontend/website"
                echo "Website directory removed."
            else
                echo "Website directory frontend/website not found (may already be clean)."
            fi
            
            echo "Blast complete! Starting with a clean state..."
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -w, --web [PORT]    Run web server after processing (default port: 8000)"
            echo "  -i, --interval MIN    Run updates every MIN minutes (requires --web)"
            echo "  --blast             Delete database and website directory for clean start"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1" >&2
            echo "Use -h or --help for usage information" >&2
            exit 1
            ;;
    esac
    shift
done

# Validate interval option
if [ $INTERVAL -gt 0 ] && [ "$SERVE_WEBSITE" != true ]; then
    echo "ERROR: --interval option requires --web to be specified" >&2
    exit 1
fi

# Detect script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if config.ini exists
if [ ! -f "config.ini" ]; then
    echo "ERROR: Configuration file 'config.ini' is missing!" >&2
    echo "Please check the project README for information on how to set up the configuration file." >&2
    exit 1
fi

# Function to check if dependencies are installed
check_dependencies() {
    echo "Checking if dependencies are installed..."
    # Try to import requests package as a sentinel for all dependencies
    if python -c "import requests" &>/dev/null; then
        echo "Dependencies are already installed."
        return 0
    else
        echo "Some dependencies are missing."
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    echo "Installing dependencies from requirements.txt..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to install dependencies." >&2
            return 1
        fi
        echo "Dependencies installed successfully."
        return 0
    else
        echo "ERROR: requirements.txt not found." >&2
        return 1
    fi
}

# Check if already in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Not in a virtual environment, checking for venv directory..."
    
    # Check if venv directory exists
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
        
        # Double check that activation worked
        if [ -z "$VIRTUAL_ENV" ]; then
            echo "ERROR: Failed to activate virtual environment." >&2
            exit 1
        fi
        echo "Virtual environment activated successfully."
    else
        echo "ERROR: Virtual environment (venv) not found." >&2
        echo "Please create a virtual environment first with:" >&2
        echo "  python -m venv venv" >&2
        echo "  source venv/bin/activate" >&2
        echo "  pip install -r requirements.txt  # if applicable" >&2
        exit 1
    fi
else
    echo "Already in virtual environment: $VIRTUAL_ENV"
fi

# Check and install dependencies if needed
if ! check_dependencies; then
    echo "Need to install dependencies..."
    if ! install_dependencies; then
        echo "ERROR: Failed to install required dependencies." >&2
        exit 1
    fi
    
    # Verify installation was successful
    if ! check_dependencies; then
        echo "ERROR: Dependencies still missing after installation attempt." >&2
        exit 1
    fi
fi

# Function to run the main processing tasks
run_processing() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] Starting data processing cycle..."
    
    # Run main.py
    echo "[$timestamp] Running main.py..."
    python main.py
    local MAIN_EXIT_CODE=$?

    if [ $MAIN_EXIT_CODE -ne 0 ]; then
        echo "[$timestamp] ERROR: main.py failed with exit code $MAIN_EXIT_CODE" >&2
        return $MAIN_EXIT_CODE
    fi
    echo "[$timestamp] main.py completed successfully."

    # Run frontend/generate_site.py
    echo "[$timestamp] Running frontend/generate_site.py..."
    python frontend/generate_site.py
    local FRONTEND_EXIT_CODE=$?

    if [ $FRONTEND_EXIT_CODE -ne 0 ]; then
        echo "[$timestamp] ERROR: frontend/generate_site.py failed with exit code $FRONTEND_EXIT_CODE" >&2
        return $FRONTEND_EXIT_CODE
    fi
    echo "[$timestamp] frontend/generate_site.py completed successfully."

    echo "[$timestamp] All tasks completed successfully!"
    return 0
}

# Run the initial processing
run_processing
PROCESSING_EXIT_CODE=$?
if [ $PROCESSING_EXIT_CODE -ne 0 ]; then
    cleanup $PROCESSING_EXIT_CODE
fi

# Start web server if requested
if [ "$SERVE_WEBSITE" = true ]; then
    WEBSITE_DIR="$SCRIPT_DIR/frontend/website"
    
    # Check if website directory exists
    if [ ! -d "$WEBSITE_DIR" ]; then
        echo "ERROR: Website directory not found at $WEBSITE_DIR" >&2
        echo "The website may not have been generated correctly." >&2
        cleanup 1
    fi
    
    echo "Starting web server on port $PORT..."
    echo "You can view the website at http://localhost:$PORT"
    
    # If interval is specified, run the web server in the background
    if [ $INTERVAL -gt 0 ]; then
        # Start web server in background
        # Start web server in background with proper process group handling
        (cd "$WEBSITE_DIR" && exec python -m http.server "$PORT") &
        SERVER_PID=$!
        sleep 1
        
        # Simple verification that server is running
        if ! ps -p $SERVER_PID >/dev/null 2>&1; then
            echo "ERROR: Web server failed to start" >&2
            cleanup 1
        fi
        
        # Store the process group ID
        SERVER_PGID=$(ps -o pgid= -p $SERVER_PID | tr -d ' ')
        echo "Web server running in background (PID: $SERVER_PID, PGID: $SERVER_PGID)"
        echo "Updates will run every $INTERVAL minutes"
        echo "Press Ctrl+C to stop all processes"
        
        # Convert minutes to seconds for sleep
        SLEEP_TIME=$((INTERVAL * 60))
        
        # Main update loop
        while true; do
            # Check if web server is still running
            if ! ps -p $SERVER_PID >/dev/null 2>&1; then
                echo "ERROR: Web server stopped unexpectedly" >&2
                cleanup 1
            fi
            
            # Sleep until next update
            echo "Next update in $INTERVAL minutes (at $(date -v +${INTERVAL}M "+%H:%M:%S"))"
            sleep $SLEEP_TIME
            
            # Run the processing tasks
            run_processing
            # Continue loop even if processing fails (to keep server running)
        done
    else
        # No interval, just run the web server in foreground
        echo "Press Ctrl+C to stop the server"
        cd "$WEBSITE_DIR"
        # Use exec to replace the current process, ensuring proper signal handling
        exec python -m http.server "$PORT"
        exit_code=$?
        
        if [ $exit_code -ne 0 ]; then
            echo "ERROR: Web server exited with code $exit_code" >&2
            cleanup $exit_code
        fi
    fi
else
    cleanup 0
fi

