from time import sleep
from datetime import datetime

import winsound
from sys import argv

from utils import *
from logger import Logger
from net_ratings import NetRatingsMgr

SECONDS_BETWEEN_PINGS = 3

EVPN    = False
VERBOSE = False
AUDIBLE = False

if len(argv) > 0:
  for i in range(len(argv)):
    match argv[i]:
      case("-evpn"):
        EVPN = True
      case("-v"):
        VERBOSE = True
      case("-a"):
        AUDIBLE = True

Logger = Logger(VERBOSE)

class ReconnecterResult:
    def __init__(self, connected, online, current_net_id, net_ratings, fail_stamps):
        self.datetime       = datetime.now()
        self.connected      = connected
        self.online         = online
        self.current_net_id = current_net_id
        self.net_ratings    = net_ratings
        self.fail_stamps    = fail_stamps


class Reconnecter:
  def __init__(self):
    self.current_net_id = ""
    self.net_ratings_mgr = NetRatingsMgr(seconds_between_pings=SECONDS_BETWEEN_PINGS, logger=Logger)
    self.net_profiles = []
    
    #getting network profiles on this computer:
    profiles_res = run_proc("netsh wlan show profile")
    profiles_res = profiles_res.split("User profiles")[1]
    profiles_res = parse_cmd_output(profiles_res)
    
    for line in profiles_res:
      if ":" in line:
        profile = netsh_info_to_val(line)
        self.net_profiles.append(profile)
    
    Logger.log(f"network profiles found: {self.net_profiles}")

    
    #what is current network connection on startup?:
    if self.am_i_on_wifi():
      self.update_current_net_id()
      Logger.log(f"on startup, connected to: {self.current_net_id}")
      self.net_ratings_mgr.update_strength(self.current_net_id)
    else:
      Logger.log("not connected to a network on startup")

    if self.am_i_online():
      self.previously_online = True
      Logger.log("online on startup")
    else:
      self.previously_online = False
      Logger.log("not online on startup")
      
  #bool
  def am_i_online(self):
    connected_res = run_proc("amIOnline.bat")
    parsed_1 = connected_res.split("'")[1]
    parsed_2 = parsed_1.split("\\")[0]
    p_res = parsed_2.strip()

    Logger.log(p_res)

    if p_res == "online":
      return True
    elif p_res == "not online":
      return False

    return False

  def am_i_on_wifi(self):
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)
    for line in interfaces_res:
      if "Signal" in line:
        return True
    return False
    

  def update_current_net_id(self, given_net_id = None):

    if given_net_id:
      self.current_net_id = given_net_id
      return
    
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)

    net_ids = []
    
    for line in interfaces_res:
      if "SSID" in line:
        net_id = netsh_info_to_val(line)
        net_ids.append(net_id)
        
    if len(net_ids) >= 1:
      self.current_net_id = net_ids[0]
    else:
      self.current_net_id = ""

  def reconnect(self):
    nets_res = run_proc("netsh wlan show networks")
    nets_res = parse_cmd_output(nets_res)
    net_ids = []

    for line in nets_res:
      if "SSID" in line:
        net_id = netsh_info_to_val(line)
        net_ids.append(net_id)

    valid_net_ids = [id for id in net_ids if id in self.net_profiles]

    Logger.log(f"valid network ids: {valid_net_ids}")

    best_net_id = self.net_ratings_mgr.choose_best(valid_net_ids)
    Logger.log(f"attempting to connect to {best_net_id}...")
    connect_cmd = f'netsh wlan connect ssid="{best_net_id}" name="{best_net_id}"'
    connect_res = run_proc(connect_cmd)
    Logger.log(connect_res)

    return best_net_id


  def public_loop(self):
    if self.am_i_online():
      if self.previously_online == False:
        if AUDIBLE:
          winsound.PlaySound('./sfx/connected.wav', winsound.SND_FILENAME)
      
      self.net_ratings_mgr.register_connected_time(self.current_net_id)

      self.previously_online = True
    else:
      if AUDIBLE:
        print('\a')
        #winsound.PlaySound('./sfx/disconnected.wav', winsound.SND_FILENAME)
      
      if self.current_net_id != "":
        self.net_ratings_mgr.register_fail(self.current_net_id)

      if self.am_i_on_wifi():
        run_proc("netsh wlan disconnect")
        
      net_id = self.reconnect()
      sleep(1)
      
      self.update_current_net_id(net_id)
      if self.am_i_on_wifi():
        self.net_ratings_mgr.update_strength(self.current_net_id)
      else:
        Logger.log("error - just reconnected but not on wifi")

      if not self.am_i_online():
        Logger.log("error - just reconnected but not online")

      self.previously_online = False

    return ReconnecterResult(
      connected=self.am_i_on_wifi(),
      online=self.am_i_online(),
      current_net_id=self.current_net_id, 
      net_ratings=self.net_ratings_mgr.net_ratings,
      fail_stamps=self.net_ratings_mgr.fail_stamps
    )
  
MAX_FAIL_DETAILS = 20

def update_console(result):
  clear()
  print(f"Time between pings: {SECONDS_BETWEEN_PINGS} seconds")
  print(f"Last update: {datetime_formatted(result.datetime)}")         
  print(f"Connected: {str(result.connected)}, Online: {str(result.online)}")
  print(f"- Current Network: {result.current_net_id}")
  if result.current_net_id in result.net_ratings.keys():
    net_rating = result.net_ratings[result.current_net_id]
    print(f"  - Network Strength: {net_rating.strength} (on last reconnect)")
    print(f"  - connected time (since startup):   {seconds_to_hours(net_rating.connected_time_since_startup)}")
    print(f"  - connected time (since reconnect): {seconds_to_hours(net_rating.connected_time_since_reconnect)}")
    print(f"  - Network Fails: {net_rating.num_fails}")
    
    i = 0
    for fail_stamp in reversed(result.fail_stamps):
      delta = seconds_to_hours((datetime.now() - fail_stamp.timestamp).total_seconds())
      print(f"    - {delta} ago, at {datetime_formatted(fail_stamp.timestamp)} - {fail_stamp.network}")
      i += 1
      if i >= MAX_FAIL_DETAILS:
        break
  
  else:
    print(f"ERROR - no network rating with net id '{result.current_net_id}'")


if __name__ == '__main__':
  Reconnecter = Reconnecter()
  while True:
    result = Reconnecter.public_loop()
    if not VERBOSE:
      update_console(result)
    sleep(SECONDS_BETWEEN_PINGS)
