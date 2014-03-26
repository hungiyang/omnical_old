import aipy as ap
import numpy as np
import commands, os, time, math, ephem
import calibration_omni as omni
FILENAME = "omnical.py"

##############Config parameters###################################
ano = 'test'##This is the file name difference for final calibration parameter result file. Result will be saved in miriadextract_xx_ano.omnical
uvfiles = ['test.uv']
wantpols = {'xx':-5, 'yy':-6}

infopaths = {'xx':'./redundantinfo_PSA32.txt', 'yy':'./redundantinfo_PSA32.txt'}
oppath = './results/'

removedegen = 1

needrawcal = True #if true, (generally true for raw data) you need to take care of having raw calibration parameters in float32 binary format freq x nant
rawpaths = {'xx':"testrawphasecalparrad_xx", 'yy':"testrawphasecalparrad_yy"}

keep_binary_data = True
########Massage user parameters
oppath += '/' 

####read redundant info################
info = [omni.read_redundantinfo(infopaths[key]) for key in wantpols.keys()]
#print info[0]['bl1dmatrix']
#exit(1)

####get some info from the first uvfile   ################
uv=ap.miriad.UV(uvfiles[0])
nfreq = uv.nchan;
nant = uv['nants'] / 2 # 'nants' counting ant-pols, so divide 2
startfreq = uv['sfreq']
dfreq = uv['sdf']
del(uv)

###read raw phase calibration prameters over frequencyfor each antenna, 203 by 32 in radiants; this part can be replaced################
if needrawcal:
	rawcalpar = np.asarray([np.fromfile(rawpaths[key], dtype="complex64").reshape(nfreq, nant) for key in wantpols.keys()])
	rawcorrection = np.zeros((len(wantpols), nfreq, nant*(nant+1)/2), dtype='complex64') + 1#to be dividing the data;  data/calpar = model
	for p in range(len(wantpols)):
		for i, bl in zip(range(len(info[p]['subsetbl'])), info[p]['subsetbl']):
			a1, a2 = info[p]['bl2d'][i]
			rawcorrection[p, :, bl] = np.conj(rawcalpar[p, :,a1]) *  rawcalpar[p, :,a2]



###start reading miriads################
print FILENAME + " MSG:",  len(uvfiles), "uv files to be processed for " + ano
data, t, timing, lst = omni.importuvs(uvfiles, info, wantpols)
print FILENAME + " MSG:",  len(t), "slices read.",

###reorder and dump the binary data from miriad################
if not os.path.exists(oppath):
	os.makedirs(oppath)

reorder = (0,2,1)
for p, pol in zip(range(len(wantpols)), wantpols.keys()):
	print "Writing polarization: " + pol,  np.array(data[:len(t), p].shape)[np.array(reorder)]
	if needrawcal:
		(np.transpose(data[:len(t), p],reorder)/rawcorrection[p, np.newaxis,:,:]).tofile(oppath + 'miriadextract_' + pol + '_' + ano)
	else:
		np.transpose(data[:len(t), p],reorder).tofile(oppath + 'miriadextract_' + pol + '_' + ano)	

###Save various files read################
#np.savetxt('miriadextract_' + ano + "_sunpos.dat", sunpos[:len(t)], fmt='%8.5f')
f = open(oppath + 'miriadextract_' + ano + "_localtime.dat",'w')
for time in timing:
	f.write("%s\n"%time)
f.close()
f = open(oppath + 'miriadextract_' + ano + "_lsthour.dat",'w')
for l in lst:
	f.write("%s\n"%l)
f.close()
del(data)

####Call C++ omnical code################
for p, pol in zip(range(len(wantpols)), wantpols.keys()):
	command = "./omnical " + oppath + 'miriadextract_' + pol + '_' + ano + " " + infopaths[pol] + " " + str(len(t)) + " " + str(nfreq) + " "  + str(nant) + " " + str(removedegen)# + " " + oppath + 'miriadextract_' + pol + '_' + ano + ".omnical"
	print FILENAME + " MSG: System call: ",  command
	os.system(command)
	print np.fromfile(oppath + 'miriadextract_' + pol + '_' + ano + ".omnical", dtype = 'float32').reshape((len(t), nfreq, 3+2*(info[p]['nAntenna']+info[p]['nUBL'])))[:5,50,:3]
	if not keep_binary_data:
		os.remove(oppath + 'miriadextract_' + pol + '_' + ano)


#########Test results############
newresult = np.fromfile(oppath + "miriadextract_xx_test.omnical", dtype = 'float32')
correctresult = np.fromfile("test.omnical", dtype = 'float32')
if newresult.all() == correctresult.all():
	print "TEST PASSED!"
else:
	print "TEST FAILED :("
for p, pol in zip(range(len(wantpols)), wantpols.keys()):
	os.remove(oppath + 'miriadextract_' + pol + '_' + ano + '.omnical')
os.remove(oppath + 'miriadextract_' + ano + "_localtime.dat")
os.remove(oppath + 'miriadextract_' + ano + "_lsthour.dat")
