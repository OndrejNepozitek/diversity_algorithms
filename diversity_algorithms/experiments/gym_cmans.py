
# coding: utf-8

## EA & pyMaze expriments - vanilla python version for SCOOP parallelism
import sys,getopt
import numpy as np

import gym, gym_fastsim

from diversity_algorithms.environments import EvaluationFunctor
from diversity_algorithms.controllers import SimpleNeuralController
from diversity_algorithms.analysis import build_grid
from diversity_algorithms.algorithms.stats import * 

from diversity_algorithms.algorithms import grid_features

from deap import creator, base

import dill
import pickle
import math

# =====
# Yes, this is ugly. This is DEAP's fault.
# See https://github.com/DEAP/deap/issues/57

from diversity_algorithms.algorithms.cma_ns import set_creator_cmans
set_creator_cmans(creator)

from diversity_algorithms.algorithms.cma_ns import cmans, Indiv_CMANS
from diversity_algorithms.algorithms.utils import *

from diversity_algorithms.experiments.exp_utils import *
 
creator.create("MyFitness", base.Fitness, weights=(1.0,1.0))
creator.create("Individual", Indiv_CMANS, typecode="d", fitness=creator.MyFitness, strategy=None)
#creator.create("Strategy", list, typecode="d")

# =====


with_scoop=True

if with_scoop:
	from scoop import futures


# Each worker gets a functor
nnparams={"n_hidden_layers": 2, "n_neurons_per_hidden": 10}
#env, controller = generate_gym_env_and_controller(params=nnparams)
eval_gym = EvaluationFunctor(controller_type=SimpleNeuralController,controller_params=nnparams,get_behavior_descriptor='auto')

# DO NOT pass the functor directly to futures.map -- this creates memory leaks
# Wrapper that evals with the local functor
def eval_with_functor(g):
	return eval_gym(g)

# declaration of params: RunParam(short_name (single letter for call from command line), default_value, doc)
params={
	"verbosity": RunParam("v", "none", "verbosity level (all, none or module specific values"),
	"pop_size": RunParam("p", 10, "population size (mu)"),
	"lambda": RunParam("l", 2., "Number of offspring generated (coeff on pop_size)"),
	"env_name": RunParam("e", "FastsimSimpleNavigation-v0", "gym environment name"),
	"nb_gen":   RunParam("g", 100, "number of generations"),
	"evolvability_period": RunParam("V", 100, "period of evolvability estimation"),
	"dump_period_bd": RunParam("b", 1, "period of behavior descriptor dump"),
	"dump_period_pop": RunParam("d", 1, "period of population dump"),
	"variant": RunParam("a", "CMANS", "variant of the CMA Novelty Search algorithm"),
	"cxpb": RunParam("", 0, "cross-over rate"), # No crossover
	"mutpb": RunParam("",1., "mutation rate"),  # All offspring are mutated...
	"indpb": RunParam("",0.1, "indiv probability"), # ...but only 10% of parameters are mutated
	"eta_m": RunParam("", 15.0, "Eta parameter for polynomial mutation"),
	"min": RunParam("", -5., "Min value of the genotype"), # WARNING, some variants do not use it at all. -5 seems reasonable for NN weights
	"max": RunParam("", 5., "Min value of the genotype"), # WARNING, some variants do not use it at all. 5 seems reasonable for NN weights
	"k": RunParam("", 15, "Number of neighbors to take into account for novelty computation"),
	"add_strategy": RunParam("s", "random", "strategy for archive inclusion (random or novel)"),
	"lambda_nov": RunParam("", 6, "number of indiv added to the archive at each gen"),
	"geno_type": RunParam("G", "realarray", "type of genotype (either realarray or dnn)"),
	"ccov": RunParam("c", 0.2, "coeff of the sample estimated C in the covariance matrix update"),
	"cmamu": RunParam("m", 10, "number of samples to generate to update C"),
	"sigma": RunParam("S", 1, "sigma coefficient for covariance matrix update")
	}

analyze_params(params, sys.argv)
	
eval_gym.set_env(None,params["env_name"].get_value(), with_bd=True)


# THIS IS IMPORTANT or the code will be executed in all workers
if(__name__=='__main__'):
	# Get env and controller

	sparams, pool=preparing_run(eval_gym, params, with_scoop)
	
	pop, archive, logbook = cmans(eval_with_functor, sparams, pool)

	terminating_run(sparams, pop, archive, logbook)

	
