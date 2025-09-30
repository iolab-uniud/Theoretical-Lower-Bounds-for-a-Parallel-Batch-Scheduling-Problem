def get_n_jobs(instance_number):
    if instance_number < 21:
        return "10 jobs"
    elif instance_number < 41:
        return "25 jobs"
    elif instance_number < 61:
        return "50 jobs"
    elif instance_number < 81:
        return "100 jobs"
    elif instance_number < 101:
        return "250 jobs"
    elif instance_number < 121:
        return "500 jobs"
    return "xx jobs"

def get_size(instance_number):
    if instance_number < 21:
        return "small"
    elif instance_number < 41:
        return "small"
    elif instance_number < 61:
        return "medium"
    elif instance_number < 81:
        return "medium"
    elif instance_number < 101:
        return "large"
    elif instance_number < 121:
        return "large"
    return "xx"

def get_instance_code(instance_string):
    instance_string = instance_string.split("/")[-1].replace("warm_start_","")
    if "NewRandom" in instance_string:
        return int(instance_string.split("NewRandom")[0])
    elif "Random" in instance_string:
        return int(instance_string.split("Random")[0])
    
def perc_gap(sol,lb):
    if round(sol,6) == 0.0 and round(lb,6) == 0.0:
        return 0.0
    return round(100*(sol-lb)/sol,2)

def which_better(sol,lb):
    if float(lb) > float(sol):
        return "calc."
    elif float(lb) < float(sol):
        return "solv."
    return "equ."

def gap_type(gap):
    if gap > 0.0 and gap <= 1. :
        return "0% < gap ≤ 1%"
    if gap > 1. and gap <= 5. :
        return "1% < gap ≤ 5%"
    if gap > 5.:
        return "gap > 5%"
    return "gap = 0%"
    
def calc_complete_objective(normalizer, pr, norm_pr, sc, norm_sc, t, norm_t):
    return ((pr * norm_pr + sc * norm_sc + t * norm_t)/normalizer)

def calc_complete_objective_integer (normalizer, pr, norm_pr, sc, norm_sc, t, norm_t):
    return (pr * norm_pr + sc * norm_sc + t * norm_t)