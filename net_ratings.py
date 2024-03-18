from logger import logger
from utils import *

class net_rating:
  def __init__(self, strength, logger):
    self.strength = strength
    self.logger = logger
    self.connected_time_since_startup = 0
    self.connected_time_since_reconnect = 0
    self.num_fails = 0
    self.fail_timestamps = []
    self.logger.log(f" - new net rating, initial strength: {strength}")

  def update_strength(self, strength):
    self.strength = strength
    self.logger.log(f" - updating net rating's strength: {strength}")

  def register_connected_time(self, seconds_between_pings):
    self.connected_time_since_startup += seconds_between_pings
    self.connected_time_since_reconnect += seconds_between_pings  
    self.logger.log(f" - updated net rating's connected time since startup:   {self.connected_time_since_startup}")
    self.logger.log(f" - updated net rating's connected time since reconnect: {self.connected_time_since_reconnect}")

  def register_fail(self):
    self.num_fails += 1
    self.logger.log(f" - updated net rating's num fails: {self.num_fails}")
    self.connected_time_since_reconnect = 0
    self.fail_timestamps.append(datetime.now())

  def get_score(self):
    connected_time = self.connected_time_since_startup 
    if connected_time == 0:
      score = self.num_fails * -1 
    elif self.num_fails > 0:
      score = connected_time / self.num_fails
    else:
      score = connected_time #shouldn't ever happen
      
    self.logger.log(f" - strength:                         {self.strength}")
    self.logger.log(f" - connected time (since startup):   {seconds_to_hours(self.connected_time_since_startup)}")
    self.logger.log(f" - connected time (since reconnect): {seconds_to_hours(self.connected_time_since_reconnect)}")
    self.logger.log(f" - num fails:                        {self.num_fails}")
    self.logger.log(f" - score:                            {score}")

    return score
  
    # todo: factor in signal strength
    # todo: handle times when there is no network to choose from
    # coulddo: factor in times when we weren't online yet we were connected to the network
  
    

# returns strength int
class net_ratings_mgr:
  def __init__(self, seconds_between_pings, logger):
    self.seconds_between_pings = seconds_between_pings
    self.logger = logger
    self.net_ratings = { }

  def current_strength(self):
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)

    signal_strs = []

    for line in interfaces_res:
      if "Signal" in line:
        signal_str = netsh_info_to_val(line)
        signal_strs.append(signal_str)

    if len(signal_strs) == 1:
      strength = signal_strs[0].strip("%")
      strength = int(strength)
      return strength
    elif len(signal_strs) == 0:
      self.logger.log("error - tried to find signal strength when not connected")
      self.logger.log("  result of show interfaces cmd:") 
      for line in interfaces_res:
        self.logger.log(line)
      return -1
    else:
      self.logger.log("error - multiple signal strength values found")
      self.logger.log("  result of show interfaces cmd:") 
      for line in interfaces_res:
        self.logger.log(line)
      return -1

  def update_strength(self, net_id):
    if net_id in self.net_ratings:
      self.logger.log(f"updating net rating for {net_id}")
      self.net_ratings[net_id].update_strength(self.current_strength())
    else:
      self.logger.log(f"adding net rating for {net_id}")
      self.net_ratings.update({net_id : net_rating(self.current_strength(), self.logger)})

  def register_connected_time(self, net_id):
    if net_id in self.net_ratings:
      self.logger.log(f"registering connected time in net rating for {net_id}")
      self.net_ratings[net_id].register_connected_time(self.seconds_between_pings)
    else:
      self.logger.log(f"adding net rating for {net_id} to register connected time")
      self.logger.log("  error - net rating should already exist before registering connected time")
      self.net_ratings.update({net_id : net_rating(self.current_strength(), self.logger)})
      self.net_ratings[net_id].register_connected_time(self.seconds_between_pings)
      
  def register_fail(self, net_id):
    if net_id in self.net_ratings:
      self.logger.log(f"registering fail in net rating for {net_id}")
      self.net_ratings[net_id].register_fail()
    else:
      self.logger.log(f"adding net rating for {net_id} to register fail")
      self.logger.log("  error - net rating should already exist before registering a fail")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})
      self.net_ratings[net_id].register_fail()
  
  def choose_best(self, valid_net_ids):

    #1. try networks which haven't yet been tried
    for net_id in valid_net_ids:
      if net_id not in self.net_ratings:
        return net_id

    #2. try network which has had the fewest fails:
    best_net_id = None
    best_score = None
    for net_id in valid_net_ids:
      if net_id in self.net_ratings:
        self.logger.log(f"getting score for net rating: {net_id}")
        this_score = self.net_ratings[net_id].get_score()
        if (best_net_id == None) or (this_score > best_score):
          best_net_id = net_id
          best_score = this_score

    if best_net_id:
      return best_net_id