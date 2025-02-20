#!/usr/local/bin/python
from ciscoconfparse import CiscoConfParse
from os import walk, makedirs, listdir
from os.path import isfile, join, splitext, exists
import re, yaml, sys, pprint

# Explicitly specify entry point for clarity's sake
def main():

  # Permit limited configuration via command-line args
  debug = False                         # Debug YAML to console defaults to off: enable with --debug
  root_path = 'configurations/'         # Root dir is 'configurations': modify with --root="mydir"
  domain = 'acme.intern'                # Default domain is 'nwid.bris.ac.uk': modify with --domain="mydomain"
  if (len(sys.argv) > 1):
    for arg in sys.argv:
      if arg == '--debug':
        debug = True
      if arg[:6] == '--root':
        head, sep, directory_value = arg.partition('=')
        if directory_value != '':
          root_path = directory_value.replace('"', '') + '/'
      if arg[:8] == '--domain':
        head, sep, domain_value = arg.partition('=')
        if domain_value != '':
          domain = domain_value.replace('"', '')
  
  subdirs = []   # obtain all subdirectories
  subdirs.append('')                    # add root directory

  # Parse all files in all subdirectories
  for subdir in subdirs:
    files = [filename for filename in listdir(root_path + subdir) if isfile(join(root_path + subdir, filename))]
    for filename in files:
      if filename != '.gitignore':                                              # Do not parse .gitignores
        input = CiscoConfParse(root_path + subdir + '/' + filename)             # Get our CiscoConfParse-formatted input
        output_yaml = convert_to_yaml(input)                                    # Parse input config into output YAML
        output_path = 'yaml/' + subdir
        print('Outputting ' + output_path + filename + '.' + domain + '.yml YAML')
        write_output_yaml_to_file(output_yaml, output_path, filename, domain)   # Write our YAML to disk
        regex_yaml(output_path + filename + '.' + domain +'.yml')               # Perform regex search and replace on the YAML
        if (debug):                                                             # If debug mode specified output YAML to console
          print(output_path + splitext(filename)[0] + '.' + domain + '.yml YAML Output:')
          print(output_yaml)


# The workhorse function that reads the Cisco config and returns our output config object
def convert_to_yaml(input_config):
  output_config = {} # Create master dict for output data

  # Interfaces
  interfaces = input_config.find_objects(r'interface')     # Create interfaces object
  if interfaces:
    output_config['interfaces'] = []            # Create list of interfaces
    for interface in interfaces:
      # dict for this particular interface
      interface_dict = {}

      # Insert interface name
      interface_name = interface.re_match(r'^interface (\S+)$')
      if interface_name:
          interface_dict['aname'] = interface_name

      # switchport

      # Find list of interfaces with "switchport" config
      switchport_interfaces = interface.re_search_children(r'switchport')
      if switchport_interfaces:

        # Create switchport dict if it does not yet exist
        #if not 'switchport' in interface_dict:
         # interface_dict['switchport'] = {}

        for line in switchport_interfaces:

          # access vlan
          access_vlan = line.re_match(r' switchport access vlan (\S+)')
          if access_vlan:
            interface_dict['vlan_id'] = access_vlan

          # access vlan
          voice_vlan = line.re_match(r' switchport voice vlan (\S+)')
          if voice_vlan:
            interface_dict['voice_vlan'] = voice_vlan

          # switchport mode
          switchport_mode = line.re_match(r'^ switchport mode (\S+)$')
          if switchport_mode:
            interface_dict['switchport_mode'] = switchport_mode

          # # port-security
          # port_sec = line.re_search(r'^ switchport port-security$')
          # if port_sec:
          #   interface_dict['switchport']['port_security'] = True
            
          # port-security dict
          port_sec = interface.re_search_children(r'switchport port-security')
          if port_sec:
            if not 'port_security' in interface_dict:
              interface_dict['port_security'] = {}

            for line in port_sec:

              # enabled
              port_sec_bool = line.re_search(r'^ switchport port-security$')
              if port_sec_bool:
                interface_dict['port_security']['enabled'] = True
              
              # maximum
              port_sec_max = line.re_match(r'^ switchport port-security maximum (\S+)$')
              if port_sec_max:
                interface_dict['port_security']['maximum'] = port_sec_max

          # nonegotiate
          nonegotiate = line.re_search(r'^ switchport nonegotiate$')
          if nonegotiate:
            interface_dict['nonegotiate'] = True

          # switchport trunk
          switchport_trunk = line.re_search(r'^ switchport trunk.*$')
          if switchport_trunk:

            # Create the trunk dict if it does not yet exist
            #if not 'trunk' in interface_dict['switchport']:
            #  interface_dict['trunk'] = {}

            # native vlan
            native_vlan = line.re_match(r'^ switchport trunk native vlan (\S+)$')
            if native_vlan:
              interface_dict['native_vlan'] = native_vlan

            # allowed vlan
            allowed_vlan = line.re_match(r'^ switchport trunk allowed vlan (\S+)$')
            if allowed_vlan:
              interface_dict['allowed_vlan'] = allowed_vlan

            # trunk encapsulation
            encapsulation = line.re_match(r'^ switchport trunk encapsulation (.+)$')
            if encapsulation:
              interface_dict['encapsulation'] = encapsulation



      # ip
      ip = interface.re_search_children(r'^ ip ')
      if ip:
        # Create ip dict if it does not yet exist
        if not 'ip' in interface_dict:
          interface_dict['ip'] = {}

        for line in ip:
          # ip address
          ip_address = line.re_match(r'^ ip address (.*)$')
          if ip_address:
            interface_dict['ip']['address'] = ip_address


          # ip dhcp snooping trust
          dhcp_snooping_trust = line.re_search(r'^ ip dhcp snooping trust$')
          if dhcp_snooping_trust:
            interface_dict['ip']['dhcp_snooping_trust'] = True

      # no ip
      no_ip = interface.re_search_children(r'^ no ip ')

      if no_ip:
        # Create ip dict if it does not yet exist
        if not 'ip' in interface_dict:
          interface_dict['ip'] = {}

        for line in no_ip:

          # no ip address
          no_ip = line.re_search(r'^ no ip address$')
          if no_ip:
            interface_dict['ip']['ip_address_disable'] = True

          # no ip route cache
          no_route_cache = line.re_search(r'^ no ip route-cache$')
          if no_route_cache:
            interface_dict['ip']['route_cache_disable'] = True

          # no ip mroute-cache
          no_mroute_cache = line.re_search(r'^ no ip mroute-cache$')
          if no_mroute_cache:
            interface_dict['ip']['mroute_cache_disable'] = True

      # misc
      misc = interface.re_search_children(r'.*')

      if misc:
        for line in misc:

          # description
          interface_description = line.re_match(r'^ description (.*)$')
          if interface_description:
            interface_dict['description'] = interface_description

          # power inline police
          power_inline_police = line.re_search(r'^ power inline police$')
          if power_inline_police:
            interface_dict['power_inline_police'] = True

          # cdp disable
          cdp_disable = line.re_search(r'^ no cdp enable$')
          if cdp_disable:
            interface_dict['cdp_disable'] = True

          # shutdown
          shutdown = line.re_search(r'^ shutdown$')
          if shutdown:
            interface_dict['shutdown'] = True

          # vrf forwarding
          vrf = line.re_match(r'^ vrf forwarding (.+)$')
          if vrf:
            interface_dict['vrf'] = vrf

          # negotiation
          negotiation = line.re_match(r'^ negotiation (.+)$')
          if negotiation:
            interface_dict['negotiation'] = negotiation

          # keepalive disable
          keepalive_disable = line.re_search(r'^ no keepalive$')
          if keepalive_disable:
            interface_dict['keepalive_disable'] = True

      # Append the completed interface dict to the interfaces list
      output_config['interfaces'].append(interface_dict)


  return yaml.dump(output_config, default_flow_style = 0, explicit_start = 0)



def write_output_yaml_to_file(output_yaml, output_path, filename, domain):
  # Make sure the directory we're trying to write to exists. Create it if it doesn't
  if not exists(output_path):
    makedirs(output_path)

  # Write foo.yml to the subdir in yaml/root_path that corresponds to where we got the input file
  with open(output_path + filename + '.' + domain + '.yml', 'w') as outfile:
    outfile.write(output_yaml)


def regex_yaml(filename):
    # Open the file and read its contents
    with open(filename, 'r') as file:
        file_contents = file.read()

    # Perform the regex search and replace to get the format of FH OOE
    file_contents = re.sub('\r\n', '\n', file_contents)
    file_contents = re.sub('  ', '    ', file_contents)
    file_contents = re.sub('- aname:', ' ', file_contents)
    file_contents = re.sub(r'(Gigabit.*?)\n', r'\1:\n', file_contents)
    file_contents = re.sub(r'(.*?vlan.*?)\'(\d*?)\'', r'\1\2', file_contents)
    file_contents = re.sub(r'(description: \'.*?)\n\s*(.*?\')', r'\1 \2', file_contents)
    file_contents = re.sub(r'(description: )\'(.*?)\'', r'\1"\2"', file_contents)

    # Write the updated contents back to the file
    with open(filename, 'w') as file:
        file.write(file_contents)


if __name__ == '__main__':
  main()
