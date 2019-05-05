import configparser

loader = configparser.ConfigParser()

def configSectionMap(section):
    dict = {}
    options = loader.options(section)
    for option in options:
        try:
            dict[option] = loader.get(section, option)
            if dict[option] == -1:
                DebugPrint("skip: %s!" % option)
        except:
            print("exception on %s!" % option)
            dict[option] = None
    return dict

def read(file):
    loader.read(file)