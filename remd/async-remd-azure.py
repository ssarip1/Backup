""" The main script for REMD on Azure 
"""

import sys
import os
import random
import time
import optparse
import logging
import re
import math
import threading
import traceback
import pdb
import ConfigParser

# import bigjob implementation (azure based)
sys.path.append('../')
sys.path.append('J:\Dr Jha Project\Backup\winazurestorage')
from bigjob_azure import *

class ReManager():
    """ 
    This class holds information about the application and replicas remotely running via Azure
    """    
    def __init__(self, config_filename):
        
        self.stage_in_file_list = []
        self.exchange_count = 0
        self.arguments = []
        
        # lists for variables of each replica (Note that these variable should have n variables where n is self.replica_count
        self.replica_count = 0
        self.temperatures = []
        
        # instant variable for replica exchange
        self.replica_jobs = []   # saga jobs
        
        # file staging
        # contains ids of staged files
        # <glidein_url, [replica_id1, ...]
        self.glidein_file_dict = {}

        self.read_config(config_filename)
        # init random seed
        random.seed(time.time()/10.)
  
        
    def read_config(self, conf_file):
        # read config file
        config = ConfigParser.ConfigParser()
        print ("read configfile: " + conf_file)
        config.read(conf_file)
        # RE configuration
        default_dict = config.defaults()        
        self.arguments = default_dict["arguments"].split()       
        self.exchange_count = config.getint("DEFAULT", "exchange_count")
        self.total_number_replica = config.getint("DEFAULT", "total_number_replica")
        self.number_of_nodes = config.getint("DEFAULT", "number_of_nodes")
        """ Config parameters (will be moved to config file in the future) """
        self.adaptive_sampling  =  config.getboolean("DEFAULT", "adaptive_sampling") 
        self.adaptive_replica_size  = config.getboolean("DEFAULT", "adaptive_replica_size") 
        
        self.temperatures = default_dict["temperature"].split()
        self.stage_in_file_list = default_dict["stage_in_file"].split()
        self.executable = default_dict["executable"]
        self.working_directory = default_dict["working_directory"]
        
  
    #####################################
    #  Elementary Functions
    ########################################################
    def get_job_description(self, replica_id):        
        jd = description()  
        jd.executable = "approot\\resources\\namd\\namd2.exe"
        #jd.number_of_processes = self.number_of_processes
        jd.spmd_variation = "single"
        jd.arguments = self.arguments
        jd.working_directory = "$TEMP"
        jd.output = "stdout"
        jd.error = "stderr"
        
        # file staging
        transfer = {}
        transfer ["source"] = os.getcwd() + "/NPT.conf" # source for staging in (see JSDL spec) 
        transfer ["target"] = jd.working_directory + "NPT.conf"     # target for staging out (see JSDL spec)   
        jd.filetransfer = [transfer]         
        return jd

    
    def submit_job(self, dest_url_string, jd):
        error_string = ""
        js = saga.job.service(saga.url(dest_url_string))
        new_job = js.create_job(jd)
        new_job.run()
        return error_string, new_job
   

    def prepare_NAMD_config(self, replica_id):
        # The idea behind this is that we can simply modify NPT.conf before submit a job to set temp and other variables
        ifile = open("NPT.conf")   # should be changed if a different name is going to be used
        lines = ifile.readlines()
        for line in lines:
            if line.find("desired_temp") >= 0 and line.find("set") >= 0:
                items = line.split()
                temp = items[2]
                if eval(temp) != self.temperatures[replica_id]:
                    print "\n (DEBUG) temperature is changing to " + str(self.temperatures[replica_id]) + " from " + temp + " for rep" + str(replica_id)
                    lines[lines.index(line)] = "set desired_temp %s \n"%(str(self.temperatures[replica_id]))
        ifile.close() 
        ofile = open("NPT.conf","w")
        for line in lines:    
            ofile.write(line)
        ofile.close()

    def get_energy(self, replica_id):
        """ parse energy out of stdout """
        stdout = self.replica_jobs[replica_id].get_stdout()
        for line in stdout.split("\n"):
            items = line.split()
            if len(items) > 0:
                if items[0] in ("ENERGY:"):
                    en = items[11]  
        print "(DEBUG) energy : " + str(en) + " from replica " + str(replica_id) 
        return eval(en)

    def do_exchange(self, energy, irep, jrep):
        iflag = False
        en_a = energy[irep]
        en_b = energy[jrep]
        
        factor = 0.0019872  # from R = 1.9872 cal/mol
        delta = (1./int(self.temperatures[irep])/factor - 1./int(self.temperatures[irep+1])/factor)*(en_b-en_a)
        if delta < 0:
            iflag = True
        else :
            if math.exp(-delta) > random.random() :
                iflag = True
    
        if iflag is True:
            tmpNum = self.temperatures[jrep]
            self.temperatures[jrep] = self.temperatures[irep]
            self.temperatures[irep] = tmpNum
    
        print "(DEBUG) delta = %f"%delta + " en_a = %f"%en_a + " from rep " + str(irep) + " en_b = %f"%en_b +" from rep " + str(jrep)


    def submit_subjob(self,  jd):
        """ submit job via pilot job"""       
        sj = subjob(bigjob=self.bj)
        sj.submit_job(jd)
        return sj
      
    def start_bigjob(self, nodes):
        """start pilot jobs (advert_job.py) at every unique machine specified in RE_info"""  
        start = time.time()
        self.bj = bigjob_azure()
        self.bj.start_pilot_job(number_nodes=nodes)
        logging.debug("BigJob Azure Initiation Time: " + str(time.time()-start))
        return self.bj
    
  
    def stop_bigjob(self):
        """ stop pilot job """
        self.bj.cancel()
  
    
    def gcd(a, b):

        '''Returns the Greatest Common Divisor,
           implementing Euclid's algorithm.
           Input arguments must be integers;
           return value is an integer.'''
        while a:
            a, b = b%a, a
        return b


    #########################################################
    #  run_REMDg
    #########################################################
    def run_REMDg(self):
        
        """ Main loop running replica-exchange """
<<<<<<< HEAD
        REMD_start = time.time()
        numEX = self.exchange_count    
        ofilename = "async-remd-temp-4M-16cores.out"
=======
        start = time.time()
        numEX = self.exchange_count    
        ofilename = "remd-temp.out"
>>>>>>> ee011da7056795d4d9bb742878ffd137e871135f
        print "Start Bigjob"
        self.bj = self.start_bigjob(self.number_of_nodes)
        if self.bj==None or self.bj.get_state_detail()=="Failed":
            return       
       
        iEX = 0
        total_number_of_namd_jobs = 0
<<<<<<< HEAD
        while (iEX < numEX):
=======
        while 1:
>>>>>>> ee011da7056795d4d9bb742878ffd137e871135f
            print "\n"
            # reset replica number
                       
            print "############# spawn jobs ################"
            self.replica_jobs = []            
            start_time = time.time()
            replica_id = 0            
            state = self.bj.get_state_detail()  
            pilot_url = self.bj.pilot_url 
            print "Pilot: " + pilot_url + " state: " + state
<<<<<<< HEAD
 
=======
             
>>>>>>> ee011da7056795d4d9bb742878ffd137e871135f
            if state.lower()== "running":
                logging.debug("pilot job running - start " + str(self.total_number_replica) + " jobs.")
                for i in range (0, self.total_number_replica):
                    #self.stage_files([os.getcwd() + "/NPT.conf"], self.blob_container, replica_id)
                    ################ replica job spawning ###########################  
                    self.prepare_NAMD_config(replica_id)
                    jd = self.get_job_description(replica_id)
                    new_job = self.submit_subjob(jd)
                    #pdb.set_trace()
                    self.replica_jobs.insert(replica_id, new_job)
                    replica_id = replica_id + 1
                    print "(INFO) Replica " + "%d"%replica_id + " started (Num of Exchange Done = %d)"%(iEX)

            end_time = time.time()        
            # contains number of started replicas
            numReplica = len(self.replica_jobs)
    
            print "started " + "%d"%numReplica + " of " + str(self.total_number_replica) + " in this round." 
            print "Time for spawning " + "%d"%numReplica + " replica: " + str(end_time-start_time) + " s"

<<<<<<< HEAD
            print  ####################################### async-job monitoring step ###############################
            energy = [0 for i in range(0, numReplica)]
            flagJobDone = [ False for i in range(0, numReplica)]
            flagExchangeDone = [ False for i in range(0, numReplica)]
            flagJobCount = [ False for i in range(0, numReplica)]
            numJobDone = 0
            print "\n" 
            #print "\n\n\n  ##################### Replica State Check at: " + time.asctime(time.localtime(time.time())) + " ########################"
            while(numJobDone < numReplica):
             print "\n##################### Replica State Check at: " + time.asctime(time.localtime(time.time())) + " ########################"
             for irep in range(0, numReplica):
                #print "\n##################### Replica State Check at: " + time.asctime(time.localtime(time.time())) + " ########################"
                running_job = self.replica_jobs[irep]
                try: 
                   state = running_job.get_state()
                except:
                   pass
                print "replica_id: " + str(irep) + " job: " + str(running_job) + " received state: " + str(state)\
                                     + " Time since launch: " + str(time.time()-REMD_start) + " sec"
                    
                if (str(state) == "Done") and (flagJobDone[irep] is False) :   
                   print "\n\n(INFO) Replica " + "%d"%irep + " done"
                   energy[irep] = self.get_energy(irep) ##todo get energy from right host
                   flagJobDone[irep] = True
                   numJobDone = numJobDone + 1
                   total_number_of_namd_jobs = total_number_of_namd_jobs + 1
                   flagJobCount[irep] = True
                   ####################################### Replica Exchange ##################################    
                   # replica exchange step        
                   print "\n(INFO)   " + "replica_id:"+ str(irep)+ " is in Done State " + " and looking for an exchange"
                   print "\n(INFO)  " + " Number of Job Done:  " + str(numJobDone) 
                   j=irep
                   frep=0
                   list=[]
                   for frep in range(0,numReplica-1):
                       running_job_frep = self.replica_jobs[frep] 
                       try:
                          state = running_job_frep.get_state()
                       except:
                          pass
                       if(str(state) == "Done" and (frep!=j) and (flagExchangeDone[frep] is False)):
                          print "\n(INFO)" + "replica_id: " + str(irep) + " found " + "replica_id: " + str(frep) + " in done state " 
                          energy[frep] = self.get_energy(frep) ##todo get energy from right host
                          flagJobDone[frep] = True
                          flagExchangeDone[irep] = True
                          flagExchangeDone[frep] = True
                          if(flagJobCount[frep] is False):
                             numJobDone= numJobDone + 1
                             total_number_of_namd_jobs = total_number_of_namd_jobs + 1
                          else:
                             pass
                          en_a = energy[frep]
                          en_b = energy[irep]
                          self.do_exchange(energy,frep, irep)
                          #list.append[frep]
                          print "\n(INFO)  " + " Number of Job Done:  " + str(numJobDone) 
                          print "\n(INFO) replica_id:" + str(irep) + " exchanged temperature with " + "replica_id: " + str(frep) + "\n\n" 
                          break
                       elif(frep==j):
                          print "\n Checking the same replica........." + str(irep)
                       elif(str(state) == "Done" and (frep!=j) and (flagExchangeDone[frep] is True)):
                         print "\n(INFO)" + "replica_id: " + str(frep) + " are in done state " + " and exchange is over  "
                       else:
                          print "\n replica_id:" + str(frep) + "  Not in Done State \n "
                          #print "\n\n (INFO) In Exchange Lookup ##################### Replica State Check at: " + time.asctime(time.localtime(time.time())) + " ########################"
                           
                elif(str(state)=="Failed"):
                  self.stop_glidin_jobs()
                  sys.exit(1)
                else:
                  pass
            
            iEX=iEX + 1        
            end_time=time.time()
            print "\n (INFO) Time for an exchange is: " + str(end_time-start_time)
            print "iEX=" + str(iEX)
            output_str = "%5d-th EX :"%iEX
            for irep in range(0, numReplica):
                output_str = output_str + "  %s"%self.temperatures[irep]

            print "\n\nExchange result : "
            print output_str + "\n\n"
       
            ofile = open(ofilename,'a')
            for irep in range(0, numReplica):
                ofile.write(" %s"%(self.temperatures[irep]))
            ofile.write(" \n")            
            ofile.close()      
        
        print "REMD Runtime: " + str(time.time()-REMD_start) + " sec; Pilot URL: " + str(self.bj.pilot_url) \
=======
            ####################################### async-job monitoring step ###############################
            print ############## async-job monitoring #################
            energy = [0 for i in range(0, numReplica)]
            flagJobDone = [ False for i in range(0, numReplica)]
            numJobDone = 0
    
            print "\n" 
            while 1:    
                #print "\n##################### Replica State Check at: " + time.asctime(time.localtime(time.time())) + " ########################"
                for irep in range(0, numReplica):
                    print "\n##################### Replica State Check at: " + time.asctime(time.localtime(time.time())) + " ########################"
                    running_job = self.replica_jobs[irep]
                    try: 
                        state = running_job.get_state()
                    except:
                        pass
                    print "replica_id: " + str(irep) + " job: " + str(running_job) + " received state: " + str(state)\
                                         + " Time since launch: " + str(time.time()-start) + " sec"
                    if (str(state) == "Done") and (flagJobDone[irep] is False) :   
                        print "(INFO) Replica " + "%d"%irep + " done"
                        energy[irep] = self.get_energy(irep) ##todo get energy from right host
                        flagJobDone[irep] = True
                        numJobDone = numJobDone + 1
                        #done_time=time.time()
                        #total_number_of_namd_jobs = total_number_of_namd_jobs + 1
                        ####################################### Replica Exchange ##################################    
                        # replica exchange step        
                        print "\n(INFO) Now trying to look for an exchange ...."
                        j=irep
                        frep=0
                        list[]
                        for frep in range(0,numReplica-1):
                          print "found a replica in Done State and looking for any other replicas in Done State"
                          print "time.asctime(time.localtime(time.time()))"
                          if(str(state) == "Done" and (frep!=j)):
                            list.append[frep]
                            print str(frep) + "......replica is in Done state"
                          elif(frep==j):
                            print "Checking the same replica...."
                          else:
                            print str(frep) + "Not in Done State"
                           
                        if len(list)!=0:
                            print "possible replicas exchange found"
                            k=0
                            for k in list:
                                if(float(energy[k] < 1) :
                                   # print time
                                   en_a = energy[k]
                                   en_b = energy[irep]
                                   self.do_exchange(energy, k, irep)
                                   print time.asctime(time.localtime(time.time()))+ " ######## exchange completed"
                                   iEX = iEX +1
                                   output_str = "%5d-th EX :"%iEX
                                   output_str = output_str + "  %s"%self.temperatures[irep]
                                   print "\n\nExchange result : "
                                   print output_str + "\n\n"
                                   print time.asctime(time.localtime(time.time()))+ " ######## exchange completed"
                                   break
                                else:
                                   print str(len(list))+ " = length of list, compared replica not selected, comparing other replicas"
                            break
                        else :
                           pass

                    elif(str(state)=="Failed"):
                        self.stop_glidin_jobs()
                        sys.exit(1)
                
            if iEX == numEX:
               break
            #time.sleep(15)
    
            ####################################### Replica Exchange ##################################    
            # replica exchange step        
            #print "\n(INFO) Now exchange step...."
            #for irep in range(0, numReplica-1):
            #    en_a = energy[irep]
            #    en_b = energy[irep+1]
            #    self.do_exchange(energy, irep, irep+1)
    
            #iEX = iEX +1
            #output_str = "%5d-th EX :"%iEX
            #for irep in range(0, numReplica):
            #    output_str = output_str + "  %s"%self.temperatures[irep]
            
            #print "\n\nExchange result : "
            #print output_str + "\n\n"
            
            #ofile = open(ofilename,'a')
            #for irep in range(0, numReplica):
            #    ofile.write(" %s"%(self.temperatures[irep]))
            #ofile.write(" \n")            
            #ofile.close()
    
            #if iEX == numEX:
            #    break
          
        
        print "REMD Runtime: " + str(time.time()-start) + " sec; Pilot URL: " + str(self.bj.pilot_url) \
>>>>>>> ee011da7056795d4d9bb742878ffd137e871135f
                + "; number replica: " + str(self.total_number_replica) \
                + "; number namd jobs: " + str(total_number_of_namd_jobs)
        # stop gliding job        
        self.stop_bigjob()

    
#########################################################
#  main
#########################################################
if __name__ == "__main__" :
<<<<<<< HEAD
    #pdb.set_trace()
=======
    pdb.set_trace()
>>>>>>> ee011da7056795d4d9bb742878ffd137e871135f
    start = time.time()
    op = optparse.OptionParser()
    op.add_option('--type','-t', default='REMD')
    op.add_option('--configfile','-c')
    op.add_option('--numreplica','-n', default='2')
    options, arguments = op.parse_args()
    
    if options != None and options.configfile!=None and options.type != None and options.type in ("REMD"):
        re_manager = ReManager(options.configfile)
        try:
            re_manager.run_REMDg() 
        except:
            traceback.print_exc(file=sys.stdout)
            print "Stop Glide-Ins"
            re_manager.stop_bigjob()
    else:
        print "Usage : \n python " + sys.argv[0] + " --type=<REMD> --configfile=<configfile> \n"
        print "Example: \n python " + sys.argv[0] + " --type=REMD --configfile=remd.conf"
        sys.exit(1)      
        
    #print "REMDgManager Total Runtime: " + str(time.time()-start) + " s"
