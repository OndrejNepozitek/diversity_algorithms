
# coding: utf-8

## EA & pyMaze expriments - vanilla python version for SCOOP parallelism
import sys,getopt
import numpy as np

import gym, gym_fastsim

from diversity_algorithms.controllers import SimpleNeuralController
from diversity_algorithms.analysis import build_grid
from diversity_algorithms.algorithms.stats import * 

from deap import creator, base

import dill
import pickle
import math

import sys

# =====
# Yes, this is ugly. This is DEAP's fault.
# See https://github.com/DEAP/deap/issues/57

from diversity_algorithms.algorithms.quality_diversity import set_creator
set_creator(creator)


creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, typecode="d", fitness=creator.FitnessMax)
#creator.create("Strategy", list, typecode="d")

from diversity_algorithms.algorithms.quality_diversity import QD
from diversity_algorithms.algorithms.utils import *

from diversity_algorithms.experiments.exp_utils import *

# =====


with_scoop=True

if with_scoop:
	from scoop import futures



with_scoop=True

if with_scoop:
	from scoop import futures

	"""QD algorithm
 
	QD algorithm. Parameters:
	:param archive_type: the archive type, can be "unstructured" or "grid"
	:param grid_n_bin: the number of bins per dimension if using a grid
	:param unstructured_neighborhood_radius: the radius of the ball where neighbors will be searched if using an unstructured archive
	:param sample_strategy: the archive sampling process (can be "random" or "novelty")
	:param add_strategy: the archive update strategy (can be "always", "never", "random" or "novelty")
	"""

# declaration of params: RunParam(short_name (single letter for call from command line), default_value, doc)
params={
	"run_dir_name": RunParam("R", "", "name of the dir in which to put the dir with the run files"),
	"verbosity": RunParam("v", "none", "verbosity level (all, none or module specific values"),
	"pop_size": RunParam("p", 100, "population size (number of offspring generated)"),
	"archive_type" : RunParam("a", "grid", "Archive type (grid or unstructured)"),
	"grid_n_bin" : RunParam("", -1, "Number of bins per dimension for grid archive (default auto = environment default)"),
	"unstructured_neighborhood_radius" : RunParam("", -1., "Replace radius for unstructured archive (default = half default grid size)"),
	"replace_strategy": RunParam("s", "random", "strategy for archive replacement (always, never, random, fitness or novelty)"),
	"sample_strategy": RunParam("s", "random", "strategy for sampling the archive (random or novelty)"),
	"env_name": RunParam("e", "Fastsim-LS2011", "Environment name"),
	"nb_gen":   RunParam("g", 100, "number of generations"),
	"dump_period_evolvability": RunParam("V", 100, "period of evolvability estimation"),
	"dump_period_bd": RunParam("b", 1, "period of behavior descriptor dump"),
	"dump_period_population": RunParam("d", 1, "period of population dump"),
	"dump_period_archive": RunParam("D", 1, "period of archive dump"),
	"cxpb": RunParam("", 0., "cross-over rate"), # No crossover
	"mutpb": RunParam("",1., "mutation rate"),  # All offspring are mutated...
	"indpb": RunParam("",0.1, "indiv probability"), # ...but only 10% of parameters are mutated
	"eta_m": RunParam("", 15.0, "Eta parameter for polynomial mutation"),
	"min": RunParam("", -5., "Min value of the genotype"), # WARNING, some variants do not use it at all. -5 seems reasonable for NN weights
	"max": RunParam("", 5., "Min value of the genotype"), # WARNING, some variants do not use it at all. 5 seems reasonable for NN weights
	"k_nov": RunParam("", 15, "Number of neighbors to take into account for novelty computation"),
	"geno_type": RunParam("G", "realarray", "type of genotype (either realarray or dnn)"),
	"eval_budget": RunParam("B", -1, "evaluation budget (ignored if -1). "),
	}

analyze_params(params, sys.argv)




# Controller definition :
# Parameters of the neural net
nnparams={"n_hidden_layers": 2, "n_neurons_per_hidden": 10}
# Create a dict with all the properties of the controller
controller_params = {"controller_type":SimpleNeuralController,"controller_params":nnparams}

# Get environment
eval_func = create_functor(params, controller_params)

# DO NOT pass the functor directly to futures.map -- this creates memory leaks
# Wrapper that evals with the local functor
def eval_with_functor(g):
	return eval_func(g)


# THIS IS IMPORTANT or the code will be executed in all workers
if(__name__=='__main__'):
	# Get env and controller

	sparams, pool=preparing_run(eval_func, params, with_scoop)
	

	pop, archive, logbook, nb_eval = QDEa(eval_with_functor, sparams, pool)

	terminating_run(sparams, pop, archive, logbook, nb_eval)



def launch_qd(env_name, pop_size, nb_gen, evolvability_period=0, dump_period_pop=10, dump_period_bd=1, archive_type="grid"):
	"""Launch a novelty search run on the maze
	
	Launch a novelty search run on the maze:
	:param pop_size: population size
	:param nb_gen: number of generations to compute
	:param evolvability_nb_samples: number of samples to estimate the evolvability of each individual in the population
	:param evolvability_period: period of the evolvability estimation
	:param dump_period_pop: period of populatin dump
	:param dump_period_bd: period of behavior descriptors dump	

	WARNING: the evolvability requires to generate and evaluate pop_size*evolvability_nb_samples just for statistics purposes, it will significantly slow down the process.
	"""
#	if (env_name not in grid_features.keys()):
#                print("You need to define the features of the grid to be used to track behavior descriptor coverage in algorithms/__init__.py")
#                return None, None

	if (env_name in grid_features.keys()):
	        min_x=grid_features[env_name]["min_x"]
	        max_x=grid_features[env_name]["max_x"]
	        nb_bin=grid_features[env_name]["nb_bin"]

	        grid=build_grid(min_x, max_x, nb_bin)
	        grid_offspring=build_grid(min_x, max_x, nb_bin)
	        stats=None
	        stats_offspring=None
	        nbc=nb_bin**2
	        nbs=nbc*2 # min 2 samples per bin
	        evolvability_nb_samples=nbs
	else:
                grid=None
                grid_offspring=None
                min_x=None
                max_x=None
                nb_bin=None
                evolvability_nb_samples=0
                nbs=0
                
	params={"IND_SIZE":eval_gym.controller.n_weights, 
		"CXPB":0, # No crossover
		"MUTPB":1., # All offspring are mutated...
		"INDPB":0.1, # ...but only 10% of parameters are mutated
		"ETA_M": 15.0, # Eta parameter for polynomial mutation
		"NGEN":nb_gen, # Number of generations
		"MIN": -5, # Seems reasonable for NN weights
		"MAX": 5, # Seems reasonable for NN weights
		"LAMBDA": pop_size,
		"K":15,
		"EVOLVABILITY_NB_SAMPLES": evolvability_nb_samples,
		"EVOLVABILITY_PERIOD":evolvability_period,
		"DUMP_PERIOD_POP": dump_period_pop,
		"DUMP_PERIOD_BD": dump_period_bd,
		"MIN_X": min_x, # not used by NS. It is just to keep track of it in the saved param file
		"MAX_X": max_x, # not used by NS. It is just to keep track of it in the saved param file
		"NB_BIN":nb_bin # not used by NS. It is just to keep track of it in the saved param file
	}


	# We use a different window size to compute statistics in order to have the same number of points for population and offspring statistics
	window_offspring=nbs/params["LAMBDA"]

	stats = None # No "population" - only do stats on offspring
	if (evolvability_period>0) and (evolvability_nb_samples>0):
		stats_offspring=get_stat_fit_nov_cov(grid_offspring,prefix="offspring_",indiv=True,min_x=min_x,max_x=max_x,nb_bin=nb_bin, gen_window_global=window_offspring)
	else:
		stats_offspring=get_stat_fit_nov_cov(grid_offspring,prefix="offspring_", indiv=False,min_x=min_x,max_x=max_x,nb_bin=nb_bin, gen_window_global=window_offspring)

	if(archive_type == "grid"):
		params["ARCHIVE_TYPE"] = "grid"
		params["ARCHIVE_ARGS"]={"bins_per_dim":50, "dims_ranges":([0,600],[0,600])}
	elif(archive_type == "archive"):
		params["ARCHIVE_TYPE"] = "archive"
		params["ARCHIVE_ARGS"]={"r_ball_replace":6} # seems comparable to the 12x12 cells ofthe grid
	else:
		print("ERROR: Unknown archive type %s" % str(params["ARCHIVE_TYPE"]))
		sys.exit(1)


	params["REPLACE_STRATEGY"]="never"
	params["SAMPLE_STRAGEGY"]="novelty"

	params["STATS"] = stats # Statistics
	params["STATS_OFFSPRING"] = stats_offspring # Statistics on offspring
	params["WINDOW_OFFSPRING"]=window_offspring
	
	
	print("Launching QD with pop_size=%d, nb_gen=%d and evolvability_nb_samples=%d"%(pop_size, nb_gen, evolvability_nb_samples))
	if (grid is None):
                print("WARNING: grid features have not been defined for env "+env_name+". This will have no impact on the run, except that the coverage statistic has been turned off")
	if (evolvability_period>0) and (evolvability_nb_samples>0):
		print("WARNING, evolvability_nb_samples>0. The run will last much longer...")

	if with_scoop:
		pool=futures
	else:
		pool=None
		
	dump_params(params,run_name)
	pop, archive, logbook = QD(eval_with_functor, params, pool, run_name, geno_type="realarray")
	dump_pop(pop,nb_gen,run_name)
	dump_logbook(logbook,nb_gen,run_name)
	dump_archive_qd(archive,nb_gen,run_name)
	
	return pop, logbook




pop_size=100
nb_gen=1000
evolvability_period=0
dump_period_pop=10
dump_period_bd=1
archive_type = "grid"
try:
	opts, args = getopt.getopt(sys.argv[1:],"he:p:g:v:b:d:a:",["env_name=","pop_size=","nb_gen=","evolvability_period=","dump_period_bd=","dump_period_pop=","archive_type="])
except getopt.GetoptError:
	print(sys.argv[0]+" -e <env_name> [-p <population size> -g <number of generations> -v <eVolvability computation period> -b <BD dump period> -d <generation dump period> archive_type=(archive|grid)]")
	sys.exit(2)
for opt, arg in opts:
	if opt == '-h':
		print(sys.argv[0]+" -e <env_name> [-p <population size> -g <number of generations> -v <eVolvability computation period> -b <BD dump period> -d <generation dump period>]")
		sys.exit()
	elif opt in ("-e", "--env_name"):
		env_name = arg
	elif opt in ("-p", "--pop_size"):
		pop_size = int(arg)
	elif opt in ("-g", "--nb_gen"):
		nb_gen = int(arg)
	elif opt in ("-a", "--archive_type"):
		archive_type = str(arg)
	elif opt in ("-v", "--evolvability_period"):
		evolvability_period = int(arg)
	elif opt in ("-b", "--dump_period_bd"):
		dump_period_bd = int(arg)
	elif opt in ("-d", "--dump_period_pop"):
		dump_period_pop = int(arg)
		
if(env_name is None):
	print("You must provide the environment name (as it ias been registered in gym)")
	print(sys.argv[0]+" -e <env_name> [-p <population size> -g <number of generations> -v <eVolvability computation period> -b <BD dump period> -d <generation dump period>]")
	sys.exit()
	
	
eval_gym.set_env(None,env_name, with_bd=True)


# THIS IS IMPORTANT or the code will be executed in all workers
if(__name__=='__main__'):
	# Get env and controller

			
	run_name=generate_exp_name(env_name+"_QD")
	print("Saving logs in "+run_name)
	dump_exp_details(sys.argv,run_name)

	pop, logbook = launch_qd(env_name, pop_size, nb_gen, evolvability_period, dump_period_pop, dump_period_bd, archive_type)

	
	dump_end_of_exp(run_name)
	
	print("The population, log, archives, etc have been dumped in: "+run_name)
	

