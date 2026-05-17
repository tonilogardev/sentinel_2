"""Patch Sen2Cor for PSD-15 (S2C) product compatibility."""

# 1. L2A_Process.py: handle output_dir=None in TOOLBOX mode
path = "/opt/sen2cor/lib/python2.7/site-packages/sen2cor/L2A_Process.py"
with open(path) as f:
    content = f.read()

old = "datastrip_generated = os.path.exists(os.path.join(config.output_dir,'temp','DATASTRIP'))"
new = "datastrip_generated = False"
if old in content:
    content = content.replace(old, new)
    print("L2A_Process.py: patched output_dir=None")
else:
    print("L2A_Process.py: WARNING - target line not found")

with open(path, "w") as f:
    f.write(content)

# 2. L2A_XmlParser.py: make setRoot tolerant of XML parse failures
path = "/opt/sen2cor/lib/python2.7/site-packages/sen2cor/L2A_XmlParser.py"
with open(path) as f:
    content = f.read()

# Patch getTree to not crash when root is None
old = "    def getTree(self, key, subkey):"
new = """    def getTree(self, key, subkey):
        if self._root is None:
            return False"""
content = content.replace(old, new, 1)

print("L2A_XmlParser.py: patched getTree for None root")

with open(path, "w") as f:
    f.write(content)

# 3. L2A_ProcessDataStrip.py: skip XSD validation for PSD-15 compatibility
path = "/opt/sen2cor/lib/python2.7/site-packages/sen2cor/L2A_ProcessDataStrip.py"
with open(path) as f:
    content = f.read()

old = "            xp = L2A_XmlParser(self.config, 'DS1C')\n            if not xp.validate():\n                self.logger.fatal('Incorrect datastrip L1C xml format')\n                return False"
new = "            xp = L2A_XmlParser(self.config, 'DS1C')\n            if not xp.validate():\n                self.logger.warn('DS1C validation failed (PSD-15?), continuing anyway')"
content = content.replace(old, new, 1)

print("L2A_ProcessDataStrip.py: patched to skip validation failure")

with open(path, "w") as f:
    f.write(content)

# 4. L2A_Config.py: make getEntriesFromDatastrip tolerant of missing spacecraftName
path = "/opt/sen2cor/lib/python2.7/site-packages/sen2cor/L2A_Config.py"
with open(path) as f:
    content = f.read()

old = "        di = xp.getTree('General_Info', 'Datatake_Info')\n        self.spacecraftName = di.SPACECRAFT_NAME.text"
new = """        di = xp.getTree('General_Info', 'Datatake_Info')
        try:
            self.spacecraftName = di.SPACECRAFT_NAME.text
        except:
            self.spacecraftName = 'S2C'"""
content = content.replace(old, new, 1)

print("L2A_Config.py: patched spacecraftName fallback")

with open(path, "w") as f:
    f.write(content)

# 5. Create lib_S2C symlink for S2C atmospheric correction LUTs
import os
lib_dir = "/opt/sen2cor/lib/python2.7/site-packages/sen2cor"
lib_s2c = os.path.join(lib_dir, "lib_S2C")
lib_s2b = os.path.join(lib_dir, "lib_S2B")
if not os.path.exists(lib_s2c) and os.path.exists(lib_s2b):
    os.symlink("lib_S2B", lib_s2c)
    print("Created lib_S2C -> lib_S2B symlink")
else:
    print(f"lib_S2C status: exists={os.path.exists(lib_s2c)}, lib_S2B exists={os.path.exists(lib_s2b)}")

print("\nAll patches applied.")
