/*********************************************
 * OPL 20.1.0.0 Model
 * Author: ML Lackner
 * Creation Date: May 6, 2021 at 11:23:57 AM
 *********************************************/
using CP;

//note: any execute block placed before the objective or constraints declaration is part of
//preprocessing; other blocks are part of postprocessing.
execute {
var p = cp.param;
p.TimeLimit = 3600; //Limits the CPU time spent solving before terminating a search. In seconds.
//p.FailLimit = 20000; //Limits the number of failures that can occur before terminating the search.
p.Workers = 1; //Sets the number of workers to run in parallel to solve your model. The default value auto corresponds to the number of CPUs available.
//p.FailureDirectedSearchEmphasis = 0.5; 
//p.SearchType = "Restart"; //DepthFirst, Restart, MultiPoint or Auto
p.RelativeOptimalityTolerance = 1e-8; //same value as used for minizinc mip solvers
}

//---------Input------------------------------------------------------------------------------------------------------

int LengthSchedulingHorizon = ...; 
range Times = 0..LengthSchedulingHorizon;

int LB_runningTimeOvens = ...;
int LB_totalSetupCosts = ...;
int LB_numberOfTardyJobs = ...;
int LB_totalNumberOfBatches = ...;
int LB_objective = ...;


//attributes
int nAttributes = ...; //number of attributes
range Attributes = 1..nAttributes;
int SetupCosts[0..nAttributes][Attributes] = ...; //setup_costs[i,j] costs for switching from attribute i to attribute j
int SetupTimes[0..nAttributes][Attributes] = ...; //setup_times[i,j] time for switching from attribute i to attribute j
tuple triplet { int a1; int a2; int setupTime; };
{ triplet } SetupTimeTriplets = {<i,j,SetupTimes[i][j]> | i in Attributes, j in Attributes};

//machines
int nMachines = ...; //number of machines
range Machines = 1..nMachines;
int MinCap[Machines] = ...; //minimum capacity per machine
int MaxCap[Machines] = ...; //maximum capacity per machine
int initState[Machines] = ...; //initial state of every machine
int nShifts = ...; //maximum number of shifts per machine
range Shifts = 1..nShifts;
int ShiftStartTimes[Machines][Shifts] = ...; //machine availability start times
int ShiftEndTimes[Machines][Shifts] = ...; //machine availability end times

//jobs
int nJobs = ...; //number of jobs
range Jobs = 1..nJobs;
{int} EligibleMachines[Jobs] = ...; //set of eligible machines for every job
int EarliestStart[Jobs] = ...; //earliest start date for every job
int LatestEnd[Jobs] = ...; //latest end date for every job
int MinTime[Jobs] = ...; //minimum time in machine for every job
int MaxTime[Jobs] = ...; //maximum time in machine for every job
int JobSize[Jobs] = ...; //occupied space in machine for every job
int Attribute[Jobs] = ...; //attribute of every job


//constants needed for the calculation of the objective function
int upper_bound_integer_objective = ...;
int mult_factor_total_runtime = ...;
int mult_factor_finished_toolate = ...;
int mult_factor_total_setuptimes = ...;
int mult_factor_total_setupcosts = ...;
int running_time_bound = ...;
int min_duration = ...;
int max_duration = ...;
int max_setup_time = ...;
int max_setup_cost = ...;

//---------Modelling of machine availability times -------------------------------------------------------------------

//Intensity step functions for machine availabilty times (see scheduling tutorial, chapter 4)
tuple Step {
int v; //availability value of machine (0 or 100)
key int x; //date up to which the availability has this value
};
//tuples need to be sorted for stepwise function
sorted {Step} Steps[m in Machines] =
{ <100, ShiftEndTimes[m][s]> | s in Shifts } union
{ <0, ShiftStartTimes[m][s]> | s in Shifts } union
{ <0, LengthSchedulingHorizon>} ;//off-shift after last on-shift until end of scheduling horizon
stepFunction AvailabilityTimes[m in Machines] =
stepwise (s in Steps[m]) { s.v -> s.x; 0 }; //last value is value of stepwise funtion after final step

//---------Decision Variables-------------------------------------------------------------------
//---------Jobs: 
dvar interval job [j in Jobs] optional in EarliestStart[j]..LengthSchedulingHorizon
	size MinTime[j]..MaxTime[j]; 
dvar interval jobOnMach [j in Jobs][m in Machines] optional in EarliestStart[j]..LengthSchedulingHorizon
	size MinTime[j]..MaxTime[j]
	intensity AvailabilityTimes[m];

//if job is not scheduled, pointer to job that is scheduled
dvar int inBatchWithJob[Jobs] in 0..nJobs;	


//interval variables for setups between jobs/batches
//setupTime[j][m] is setup before jobOnMach[j][m]
dvar interval setupTime [j in Jobs][m in Machines] optional in Times 
	size 0..max_setup_time
	intensity AvailabilityTimes[m];
	
	
//sequence variables for every machine
dvar sequence machines[m in Machines] in
	all( j in Jobs) jobOnMach [j][m] 
	types all( j in Jobs) Attribute[j];
	
//tardy jobs
dvar boolean tardy[Jobs];

//---------Objective Function & Evaluation of Solution-------------------------------------------------------------------
dexpr int totalNumberOfBatches = sum (m in Machines, j in Jobs)
	presenceOf(jobOnMach[j][m]) ;

////components of objective function 
dexpr int runningTimeOvens = sum (m in Machines, j in Jobs)
	lengthOf(jobOnMach[j][m]);
dexpr int numberOfTardyJobs = sum( j in Jobs ) 
   	tardy[j];
dexpr int totalSetupCosts = 
sum (m in Machines)
  (sum (j in Jobs)
		SetupCosts[typeOfPrev(machines[m], jobOnMach[j][m], initState[m], 0)][Attribute[j]]);
 	
dexpr int objective = 
	mult_factor_total_runtime * runningTimeOvens
	+
	mult_factor_finished_toolate * numberOfTardyJobs
	+ 
	mult_factor_total_setupcosts* totalSetupCosts
	;

minimize objective;
   

//--------- Constraints -------------------------------------------------------------------
subject to {

objective >= LB_objective;
runningTimeOvens >= LB_runningTimeOvens;
numberOfTardyJobs >= LB_numberOfTardyJobs;
totalSetupCosts >= LB_totalSetupCosts;
// totalNumberOfBatches >= LB_totalNumberOfBatches;

//bounds on objective components  
objective <= upper_bound_integer_objective;
runningTimeOvens <= running_time_bound;
numberOfTardyJobs <= nJobs;
totalSetupCosts <= nJobs * max_setup_cost;

//if job is present, it is scheduled on exactly one machine
//and is scheduled to eligible machine
forall (j in Jobs){
  alternative(job[j], all(m in Machines) jobOnMach[j][m]);
  alternative(job[j], all(m in EligibleMachines[j]) jobOnMach[j][m]);
}

//job is either scheduled or pointer is set to some other job 
//that is scheduled and has lower index
forall (j in Jobs, i in Jobs){
  (presenceOf(job[j]) && inBatchWithJob[j]==0)
  ||
  (!presenceOf(job[j]) && inBatchWithJob[j]>0);
}
forall (j in Jobs, i in Jobs){
  (inBatchWithJob[j]==i)
  =>
  (presenceOf(job[i]) && i<j);
}

//machine capacities may not be exceeded  
forall (m in Machines, j in Jobs)
  ctMachineCapcity : 
    presenceOf(jobOnMach[j][m])
  	*(JobSize[j] + sum(i in Jobs)(JobSize[i]*(inBatchWithJob[i]==j)))
    <= MaxCap[m]
;

//jobs can only be processed in the same batch if they have the same attribute,
//if processing times are compatible
//and start is after earliest start
forall (j in Jobs, i in Jobs){
  inBatchWithJob[j]==i
  =>
  (Attribute[i]==Attribute[j]
  &&
  lengthOf(job[i]) <= MaxTime[j]
  &&
  lengthOf(job[i]) >= MinTime[j]
  &&
  startOf(job[i]) >= EarliestStart[j]);
}

//jobs can only be processed together with other job if assigned machine is eligible
forall (i in Jobs, j in Jobs){
  inBatchWithJob[j] == i
  =>
  (sum (m in EligibleMachines[j])
  	presenceOf(jobOnMach[i][m]))
  == 1;
}

//batches on the same machine may not overlap 
forall(m in Machines)
	noOverlap(machines[m], SetupTimeTriplets, true);
 


//schedule setups between jobs
forall (j in Jobs, m in Machines){
  //setup is present iff job is present on machine
  presenceOf(jobOnMach[j][m]) == presenceOf(setupTime[j][m]);  
  //setup ends exactly at start of following batch
  //usage: endAtStart(a, b, delay) forces endTime(a) + delay == startTime(b)
  //is only effective if both a and b is present, otherwise the constraint is alsways fulfilled
  ctSetupDirectlyBeforeBatch:
  endAtStart(setupTime[j][m], jobOnMach[j][m], 0); 
  //setup starts after preceeding batch
  endOfPrev(machines[m], jobOnMach[j][m] , 0 , 0) <= startOf(setupTime[j][m]);
}

//length of setup times
forall (m in Machines, j in Jobs){
	  ctSetupLengthWhenPresent:
	  //usage: typeOfPrev(sequenceVar seq, intervalVar interval, int firstValue = 0, int absentValue = 0)
	  // firstValue: value to return if interval variable interval is the first one in seq.
      //absentValue: value to return if interval variable interval becomes absent. 
	  (lengthOf(setupTime[j][m]) == SetupTimes[typeOfPrev(machines[m], jobOnMach[j][m], initState[m], 0)][Attribute[j]]);
}

forall (j in Jobs, m in Machines){
  	//usage of forbidExtent: whenever interval variable jobOnMach[j][m] is present, 
  	//it cannot overlap a point t where AvailabilityTimes[m](t) = 0
	forbidExtent(jobOnMach[j][m], AvailabilityTimes[m]);
	forbidExtent(setupTime[j][m], AvailabilityTimes[m]);
}


//Redundant constraint: restrict the number of batches
//(at most as many batches as there are jobs)
totalNumberOfBatches <= nJobs;

//define tardy jobs
forall (j in Jobs, i in Jobs){
  (presenceOf(job[j]) && endOf(job[j]) > LatestEnd[j])
  || 
  (inBatchWithJob[j]==i && endOf(job[i]) > LatestEnd[j])
  =>
  tardy[j]==1;
}
}



//--------- Output -------------------------------------------------------------------

execute {
//when is job scheduled
for (var j in Jobs){
  for (var m in Machines){
      	if (jobOnMach[j][m].present)
      		writeln ("Job " + j + " is assigned to machine " + m + ": " + jobOnMach[j][m].start + ".." + jobOnMach[j][m].end  );
  }
}
}	

//create ouput for evaluation of results
execute {
  writeln ("objective = " + objective + "; ");
  writeln ("running_time_oven = " + runningTimeOvens + "; ");
  writeln ("total_setup_costs = " + totalSetupCosts + "; ");
  writeln ("finished_too_late = " + numberOfTardyJobs + "; ");
  writeln ("number of jobs = " + nJobs + "; ");
  writeln ("Total number of batches: " + totalNumberOfBatches + "; ");
  writeln ("upper_bound_integer_objective: " + upper_bound_integer_objective + "; ");
}




