#!/usr/bin/python

import sys, os, os.path

gotmguiroot = os.path.join(os.path.dirname(os.path.realpath(__file__)),'..')

path = sys.path[:] 
sys.path.append(gotmguiroot)
try: 
    import scenario, common, data
finally: 
    sys.path = path

scenario.Scenario.setRoot(gotmguiroot)

# Small function for receiving progress messages when parsing data files.
nextprogress = None
progresstep = .25
def printprogress(status,progress):
    global nextprogress
    if progress>=nextprogress:
        print '%i %% done - %s' % (progress*100,status)
        nextprogress += progresstep

def main():
    # Get optional command line arguments
    targetisdir = common.getSwitchArgument('-d')
    strict = not common.getSwitchArgument('-ns')
    check = common.getSwitchArgument('-check')
    protodir = common.getNamedArgument('-p')
    targetschema = common.getNamedArgument('-v')

    # Default schema
    if targetschema==None: targetschema = scenario.savedscenarioversion

    # Check if we have the required arguments.
    # Note: sys.argv[0] contains the path name of the script.
    if len(sys.argv)<3:
        print \
"""
=============================================================================
GOTM-GUI scenario import utility
=============================================================================
This utility allows you to convert existing namelist-based scenarios for
command-line GOTM to the GOTM-GUI scenario format.
-----------------------------------------------------------------------------
This script requires at least the following two arguments:

- the source file (*.tar.gz) or directory containing the namelist files.
- the target path to which to save the GOTM-GUI scenario.

If namelist data are present in one or more .values files, you must also
specify the directory with the prototype namelist files (*.proto) as follows:
-p protodir.

To force a particular version for the created scenario, add the switch
-v platform-version (e.g., -v gotm-3.2.4); by default the scenario is created
with the version that GOTM-GUI uses to store scenarios (currently %s).

To save to a directory rather than directly to a ZIP archive (which would
contain all files in the directory), add the switch -d. If you are saving to
ZIP archive rather than to a directory, use the file extension
".gotmscenario" to ensure the produced file is automatically recognized by
GOTM-GUI.

By default, namelists are parsed in "strict" mode: all variables must be
present once, and in the right order. Add the switch -ns to enable
Fortran-like loose parsing.

To check the validity of the scenario and its data files, add the switch
-check. If the scenario is found to be invalid, the script returns 1
(normally 0).

Examples:

nml2xml.py ./seagrass ./seagrass.gotmscenario

Converts the namelists (plus data files) in the directory "./seagrass" to the
scenario file "./seagrass.gotmscenario" suitable for GOTM-GUI.

nml2xml.py ./v3.2/seagrass ./seagrass.gotmscenario -p ./v3.2/templates

Converts the namelist .values file (plus data files) in the directory
"./v3.2/seagrass" to the scenario file "./seagrass.gotmscenario" suitable for
GOTM-GUI, while using .proto files in directory "./v3.2/templates".
=============================================================================
""" % scenario.savedscenarioversion
        return 1
        
    # Get command line arguments
    srcpath = os.path.abspath(sys.argv[1])
    targetpath = os.path.abspath(sys.argv[2])

    # Check if the source path exists.
    if not os.path.exists(srcpath):
        print 'Error! The source path "%s" does not exist.' % srcpath
        return 1

    # Check if we have an XML schema for the specified target scenario version.
    schemas = scenario.Scenario.getDefaultSchemas()
    if targetschema not in schemas:
        print 'Error! No XML schema available for specified output version "%s".' % targetschema
        return 1

    # Check if the target path already exists (currently only produces warning and continues).
    if os.path.exists(targetpath):
        print 'Warning! The target path "%s" exists; it may be overwritten.' % targetpath

    # Warn for alternative file extension.
    if (not targetisdir) and (not targetpath.endswith('.gotmscenario')):
        print 'Warning! The output file does not have extension .gotmscenario, and will therefore not be recognized automatically by the GUI.'

    # Try to parse the namelist files (implicitly converts to the specified target version).
    try:
        scen = scenario.Scenario.fromNamelists(srcpath,protodir=protodir,targetversion=targetschema,strict=strict)
    except Exception,e:
        print '\n\nFailed to load scenario form namelists. Reason:\n'+str(e)
        print '\nYou might try adding the switch -ns. This switch disables strict namelist parsing.'
        return 1
        
    if check:
        valid = True
        print '\n============ checking scenario validity ============'
        
        # Find used file nodes that have not been supplied with data.
        for fn in scen.root.getNodesByType('file'):
            if fn.isHidden(): continue
            value = fn.getValue(usedefault=True)
            if value==None or not value.isValid():
                print 'ERROR: variable %s points to a non-existent data file.' % '/'.join(fn.location)
                valid = False
            else:
                newstore = data.LinkedFileVariableStore.fromNode(fn)
                global nextprogress
                nextprogress = 0.
                try:
                    print 'parsing data file for %s.' % '/'.join(fn.location)
                    newstore.loadDataFile(value,callback=printprogress)
                    print 'file is valid.'
                except Exception,e:
                    print 'ERROR: could not parse data file for variable %s. Error: %s' % ('/'.join(fn.location),e)
                    valid = False

        # Find used nodes that have not been set, and lack a default value.
        for node in scen.root.getEmptyNodes():
            if node.isHidden(): continue
            defvalue = node.getDefaultValue()
            if defvalue==None:
                print 'ERROR: variable %s does not have a value but also does not have a default value associated with it.' % '/'.join(node.location)
                valid = False
            else:
                print 'WARNING: variable %s does not have a value; the default "%s" will be used.' % ('/'.join(node.location),defvalue)

        if not valid:
            print '============ validity check failed ============\n'
            return 1
        else:
            print '============ validity check succeeded ============\n'

    # Export to scenario.
    scen.saveAll(targetpath,targetversion=targetschema,targetisdir=targetisdir)

    # Clean-up (delete temporary directories etc.)
    scen.release()
    
    return 0

# If the script has been run (as opposed to imported), enter the main loop.
if (__name__=='__main__'):
    ret = main()
    sys.exit(ret)
