#!/usr/bin/env python3
"""
CommandPad Companion Application
Monitors system volume and currently playing media, sends updates to macropad via serial.

Requirements:
pip install psutil pycaw comtypes serial

For media info (Windows):
pip install winrt-Windows.Media.Control

For cross-platform media (alternative):
pip install pynput
"""

import serial
import time
import json
import threading
import sys
import traceback

# Platform-specific imports
import platform
if platform.system() == "Windows":
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        WINDOWS_AUDIO = True
    except ImportError:
        print("Windows audio libraries not found. Install: pip install pycaw comtypes")
        WINDOWS_AUDIO = False
    
    try:
        import asyncio
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
        WINDOWS_MEDIA = True
    except ImportError:
        print("Windows media libraries not found. Install: pip install winrt-Windows.Media.Control")
        WINDOWS_MEDIA = False
else:
    WINDOWS_AUDIO = False
    WINDOWS_MEDIA = False

class CommandPadCompanion:
    def __init__(self, port="COM3", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        
        # Audio monitoring
        self.last_volume = -1
        self.volume_endpoint = None
        
        # Media monitoring
        self.last_media_info = {}
        self.media_session = None
        
        self.setup_audio()
        
    def setup_audio(self):
        """Initialize Windows audio monitoring"""
        if not WINDOWS_AUDIO:
            print("Windows audio monitoring not available")
            return
            
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume_endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            print("Audio monitoring initialized")
        except Exception as e:
            print(f"Failed to initialize audio monitoring: {e}")
            
    async def get_media_info(self):
        """Get current media information (Windows only)"""
        if not WINDOWS_MEDIA:
            return None
            
        try:
            sessions = await MediaManager.request_async()
            current_session = sessions.get_current_session()
            
            if current_session:
                info = await current_session.try_get_media_properties_async()
                playback_info = current_session.get_playback_info()
                
                return {
                    'title': info.title or "Unknown",
                    'artist': info.artist or "",
                    'is_playing': playback_info.playback_status == 4,  # Playing status
                }
        except Exception as e:
            print(f"Media info error: {e}")
            
        return None
        
    def get_volume_level(self):
        """Get current system volume level (0-100)"""
        if not self.volume_endpoint:
            return None
            
        try:
            volume = self.volume_endpoint.GetMasterScalarVolume()
            return int(volume * 100)
        except Exception as e:
            print(f"Volume error: {e}")
            return None
            
    def connect_serial(self):
        """Connect to the macropad via serial"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"Connected to {self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False
            
    def send_to_macropad(self, message):
        """Send a message to the macropad"""
        if not self.serial_conn:
            return
            
        try:
            self.serial_conn.write(f"{message}\\n".encode())
            self.serial_conn.flush()
        except Exception as e:
            print(f"Serial send error: {e}")
            
    def monitor_volume(self):
        """Monitor volume changes"""
        while self.running:
            try:
                current_volume = self.get_volume_level()
                if current_volume is not None and current_volume != self.last_volume:
                    self.send_to_macropad(f"VOL:{current_volume}")
                    self.last_volume = current_volume
                    print(f"Volume: {current_volume}%")
                    
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                print(f"Volume monitoring error: {e}")
                time.sleep(1)
                
    async def monitor_media(self):
        """Monitor media changes"""
        while self.running:
            try:
                media_info = await self.get_media_info()
                
                if media_info and media_info != self.last_media_info:
                    is_playing = 1 if media_info['is_playing'] else 0
                    title = media_info['title'][:50]  # Limit length
                    artist = media_info['artist'][:30]  # Limit length
                    
                    message = f"MEDIA:{is_playing}|{title}|{artist}"
                    self.send_to_macropad(message)
                    self.last_media_info = media_info
                    
                    status = "Playing" if media_info['is_playing'] else "Paused"
                    print(f"Media ({status}): {artist} - {title}")
                    
                elif not media_info:
                    # No media playing
                    if self.last_media_info:
                        self.send_to_macropad("STOP")
                        self.last_media_info = {}
                        print("No media playing")
                        
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                print(f"Media monitoring error: {e}")
                await asyncio.sleep(2)
                
    def run_volume_thread(self):
        """Run volume monitoring in a separate thread"""
        volume_thread = threading.Thread(target=self.monitor_volume)
        volume_thread.daemon = True
        volume_thread.start()
        return volume_thread
        
    async def run_async(self):
        """Run the companion app with async media monitoring"""
        self.running = True
        
        if not self.connect_serial():
            print("Cannot continue without serial connection")
            return
            
        print("Starting monitoring...")
        print("Press Ctrl+C to stop")
        
        # Start volume monitoring thread
        volume_thread = self.run_volume_thread()
        
        try:
            # Run media monitoring
            await self.monitor_media()
        except KeyboardInterrupt:
            print("\\nShutting down...")
        finally:
            self.running = False
            if self.serial_conn:
                self.serial_conn.close()
                
    def run(self):
        """Run the companion app"""
        if WINDOWS_MEDIA:
            # Use async media monitoring on Windows
            asyncio.run(self.run_async())
        else:
            # Fallback to volume-only monitoring
            self.running = True
            
            if not self.connect_serial():
                print("Cannot continue without serial connection")
                return
                
            print("Starting volume monitoring only...")
            print("Press Ctrl+C to stop")
            
            volume_thread = self.run_volume_thread()
            
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\\nShutting down...")
            finally:
                self.running = False
                if self.serial_conn:
                    self.serial_conn.close()

def find_macropad_port():
    """Try to auto-detect the macropad's serial port"""
    import serial.tools.list_ports
    
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Look for CircuitPython devices
        if "CircuitPython" in str(port.description) or "CDC" in str(port.description):
            return port.device
    
    # Fallback to common Windows ports
    for port_name in ["COM3", "COM4", "COM5", "COM6"]:
        try:
            test_conn = serial.Serial(port_name, 115200, timeout=0.1)
            test_conn.close()
            return port_name
        except:
            continue
            
    return None

if __name__ == "__main__":
    print("CommandPad Companion App")
    print("=" * 40)
    
    # Auto-detect port or use command line argument
    port = None
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = find_macropad_port()
        
    if not port:
        print("Could not find macropad. Please specify port manually:")
        print("python companion_app.py COM3")
        sys.exit(1)
        
    print(f"Using port: {port}")
    
    companion = CommandPadCompanion(port)
    companion.run()
