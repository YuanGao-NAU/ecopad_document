from celery.task import task
from dockertask import docker_task
from subprocess import call,STDOUT
from jinja2 import Template
from shutil import copyfile, move
from glob import glob
import requests,os
from pymongo import MongoClient
from datetime import datetime
import zipfile
import shutil


#Default base directory 
basedir="/data/static"
spruce_data_folder="/data/local/spruce_data"
spruce_data_ws_folder="/data/local/spruce_data_ws"
forcing_data_folder="/data/static/ecopad_portal_ws2/uploads"
sev_data_folder="/data/local/SEV_data"
results_elm="/home/ubuntu/E3SM/run"
results_elm_plot="/home/ubuntu/OLMT/plots"
host= 'ecolab.nau.edu'
host_data_dir = "/{0}".format(os.environ["host_data_dir"])
#host_data_dir = "/home/ecopad/ecopad/data/static"

# "/home/ecopad/ecopad/data/static"
print host_data_dir
#print "hello-world"

@task()
def test(pars):
    task_id = str(test.request.id)
    input_a = pars["test1"]
    input_b = pars["test2"]
    docker_opts = None
    docker_cmd = "./test.o {0} {1}".format(input_a, input_b)
    result = docker_task(docker_name="test", docker_opts=None, docker_command=docker_cmd, id=task_id)
    return input_a + input_b

#New Example task
#@task()
#def sub(public=None):
#
##def sub(a, b):
#    """ Example task that subtracts two numbers or strings
#        args: x and y
#        return substraction of strings
#    """        
#  #  result = a - b
#    result_url = "https://ecolab.nau.edu/ecopad_tasks2/"
#    if public:
#        data={'tag':public,'result_url':result_url}
#        db=MongoClient('mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem',27017)
#        #db=MongoClient('ecopad_mongo',27017)
#        db.catalog.forecast.save(data)
#       # db=MongoClient('cybercom_mongo',27017)
#       # db.catalog.forecast.save(data)
#       # db=MongoClient('ecolab.nau.edu',27017)
#       # db.catalog.forecast.save(data)
#    return result_url

@task()
def teco_spruce_simulation(pars): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
	to file, and store the file in input folder.
	call teco_spruce_model.
    """
    task_id = str(teco_spruce_simulation.request.id)
    resultDir = setup_result_directory(task_id)
    #create param file 
    param_filename = create_template('SPRUCE_pars',pars,resultDir,check_params)
    #Run Spruce TECO code 
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)	
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5}".format("/data/{0}".format(param_filename),"/spruce_data/SPRUCE_old_forcing_2017.txt",
                                    "/spruce_data/SPRUCE_obs.txt",
                                    "/data", 0 , "/spruce_data/SPRUCE_da_pars.txt")
    result = docker_task(docker_name="teco_spruce",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    #os.makedirs("{0}/graphoutput".format(host_data_resultDir)) #make plot directory
    docker_opts = "-v {0}:/usr/local/src/myscripts/graphoutput:z ".format(host_data_resultDir)
    docker_cmd = None
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
   

    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
                'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
                'two_label':'Foliage','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage.png'),
                'three_label':'Wood','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood.png'),
                'four_label':'Root','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                'five_label':'Soil','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
    report_data['title']="SPRUCE Ecological Simulation Task Report"
    report_data['description']="Simulations of carbon fluxes and pool sizes for SPRUCE experiment based on user defined initial parameters."

    report = create_report('report',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url
  
#@task()
def teco_spruce_data_assimilation(pars):
    """
        DA TECO Spruce
        args: pars - Initial parameters for TECO SPRUCE
        kwargs: da_params - Which DA variable and min and max range for 18 variables

    """
    task_id = str(teco_spruce_data_assimilation.request.id)
    resultDir = setup_result_directory(task_id)
    #parm template file
    param_filename = create_template('SPRUCE_pars',pars,resultDir,check_params)
    da_param_filename = create_template('SPRUCE_da_pars',pars,resultDir,check_params)
    #if da_params:
    #    da_param_filename = create_template('spruce_da_pars',da_params,resultDir,check_params)
    #else:
    #    copyfile("{0}/ecopad_tasks2/default/SPRUCE_da_pars.txt".format(basedir),"{0}/SPRUCE_da_pars.txt".format(resultDir))
    #    da_param_filename ="SPRUCE_da_pars.txt"
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5}".format("/data/{0}".format(param_filename),"/spruce_data/SPRUCE_old_forcing_2017.txt",
                                    "/spruce_data/SPRUCE_obs.txt",
                                    "/data",1, "/data/{0}".format(da_param_filename))
    result = docker_task(docker_name="teco_spruce",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_da_viz.R {0} {1}".format("/data/Paraest.txt","/data")
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    report_data ={'zero_label':'Results','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'histogram.png')}
    report_data['title']="SPRUCE Ecological Data Assimilation Task Report"
    desc= "Multiple data streams from SPRUCE are assimilated to TECO model using MCMC algorithm. "\
            "The current dataset are mainly from pre-treatment measurement from 2011 to 2014. "\
            "This will be updated regularly when new data stream is available. 5 out of 18 parameters are constrained from pre-treatment data. "\
            "The 18 parameters are (1) specific leaf area, (2) maximum leaf growth rate, (3) maximum root growth rate, "\
            "(4) maximum stem growth rate, (5) maximum rate of carboxylation, (6) turnover rate of foliage pool, "\
            "(7) turnover rate of woody pool, (8) turnover rate of root pool, (9) turnover rate of fine litter pool, "\
            "(10) turnover rate of coarse litter pool, (11) turnover rate of fast soil pool, (12) turnover rate of slow soil pool, "\
            "(13) turnover rate of passive soil pool, (14) onset of growing degree days, (15) temperature sensitivity Q10, "\
            "(16) baseline leaf respiration, (17) baseline stem respiration, (18) baseline root respiration"
        
    report_data['description']=desc
    report_name = create_report('report_da',report_data,resultDir)
    return "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

@task()
def teco_spruce_forecast(pars,forecast_year,forecast_day,temperature_treatment=0.0,co2_treatment=380.0,da_task_id=None,public=None):
    """
        Forecasting 
        args: pars - Initial parameters for TECO SPRUCE
              forecast_year,forecast_day
    """
    task_id = str(teco_spruce_forecast.request.id)
    resultDir = setup_result_directory(task_id)
    os.makedirs("{0}/plot".format(resultDir))
    os.makedirs("{0}/input".format(resultDir))
    os.makedirs("{0}/output".format(resultDir))
    param_filename = create_template('SPRUCE_pars',pars,resultDir,check_params)
    #da_param_filename = create_template('SPRUCE_da_pars',pars,resultDir,check_params)
    da_param_filename ="SPRUCE_da_pars.txt"
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    #Set Param estimation file from DA 
    if not da_task_id:
        try:
            copyfile("{0}/Paraest.txt".format(spruce_data_folder),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/SPRUCE_da_pars.txt".format(spruce_data_folder),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt or SPRUCE_da_pars.txt".format(spruce_data_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/input/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/ecopad_tasks2/{1}/input/SPRUCE_da_pars.txt".format(basedir,da_task_id),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/input/Paraest.txt or SPRUCE_da_pars.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}".format("/data/{0}".format(param_filename),
                                    "/spruce_data/SPRUCE_old_forcing_2017.txt", "/spruce_data/SPRUCE_obs.txt",
                                    "/data",2, "/data/{0}".format(da_param_filename),
                                    "/spruce_data/Weathergenerate",forecast_year, forecast_day,
                                    temperature_treatment,co2_treatment)
    result = docker_task(docker_name="teco_spruce",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_forecast_viz.R {0} {1} {2} {3}".format("obs_file/SPRUCE_obs.txt","/data","/data",100)
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    # Yuanyuan add to reformat output data
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd = "Rscript reformat_to_csv.R {0} {1} {2} {3} {4}".format("/data","/data",100,temperature_treatment,co2_treatment)
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv_backup.R {0} {1} {2}".format("/data","/data",100)
    # docker_opts = None
    # docker_cmd = None
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP Forecast','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp_forecast.png'),
                'one_label':'ER Forecast','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er_forecast.png'),
                'two_label':'Foliage Forecast','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_forecast.png'),
                'three_label':'Wood Forecast','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood_forecast.png'),
                'four_label':'Root Forecast','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root_forecast.png'),
                'five_label':'Soil Forecast','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil_forecast.png')}
    report_data['title']="SPRUCE Ecological Forecast Task Report"
    desc = "Use constrained parameters from Data Assimilation to predict carbon fluxes and pool sizes. "
    desc = desc + "Forcing inputs are genereated by auto-regression model using historical climate data of the SPRUCE site. "
    desc = desc + "Allow users to choose which year and day to make predictations of ecosystem in response to treatment effects."
    report_data['description']=desc
    report_name = create_report('report',report_data,resultDir)
    #return {"data":"http://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id']),
    #        "report": "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],report_name)}
    result_url = "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    if public:
        data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient("mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem",27017)
        db.forecast.public.save(data)

    return result_url

@task()
def teco_spruce_forecast_cron(pars,forecast_year,forecast_day,temperature_treatment=0.0,co2_treatment=380.0,da_task_id=None,public=None):
    """
        Forecasting
        args: pars - Initial parameters for TECO SPRUCE
              forecast_year,forecast_day
    """
    task_id = str(teco_spruce_forecast_cron.request.id)
    resultDir = setup_result_directory(task_id)
    param_filename = create_template('SPRUCE_pars',pars,resultDir,check_params)
    #da_param_filename = create_template('SPRUCE_da_pars',pars,resultDir,check_params)
    da_param_filename ="SPRUCE_da_pars.txt"
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    #Set Param estimation file from DA
    if not da_task_id:
        try:
            copyfile("{0}/Paraest.txt".format(spruce_data_folder),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/SPRUCE_da_pars.txt".format(spruce_data_folder),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt or SPRUCE_da_pars.txt".format(spruce_data_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/input/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/ecopad_tasks2/{1}/input/SPRUCE_da_pars.txt".format(basedir,da_task_id),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/input/Paraest.txt or SPRUCE_da_pars.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}".format("/data/{0}".format(param_filename),
                                    "/spruce_data/SPRUCE_old_forcing.txt", "/spruce_data/SPRUCE_obs.txt",
                                    "/data",2, "/data/{0}".format(da_param_filename),
                                    "/spruce_data/Weathergenerate",forecast_year, forecast_day,
                                    temperature_treatment,co2_treatment)
    result = docker_task(docker_name="teco_spruce",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_forecast_viz.R {0} {1} {2} {3}".format("obs_file/SPRUCE_obs.txt","/data","/data",100)
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    # Yuanyuan add to reformat output data
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd = "Rscript reformat_to_csv.R {0} {1} {2} {3} {4}".format("/data","/data",100,temperature_treatment,co2_treatment)
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir) docker_cmd = "Rscript reformat_to_csv_backup.R {0} {1} {2}".format("/data","/data",100)
    # docker_opts = None docker_cmd = None
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP Forecast','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp_forecast.png'),
                'one_label':'ER Forecast','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er_forecast.png'),
                'two_label':'Foliage Forecast','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_forecast.png'),
                'three_label':'Wood Forecast','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood_forecast.png'),
                'four_label':'Root Forecast','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root_forecast.png'),
                'five_label':'Soil Forecast','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil_forecast.png')}
    report_data['title']="SPRUCE Ecological Forecast Task Report"
    desc = "Use constrained parameters from Data Assimilation to predict carbon fluxes and pool sizes. "
    desc = desc + "Forcing inputs are genereated by auto-regression model using historical climate data of the SPRUCE site. "
    desc = desc + "Allow users to choose which year and day to make predictations of ecosystem in response to treatment effects."
    report_data['description']=desc
    report_name = create_report('report',report_data,resultDir)
    #return {"data":"http://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id']),
    #        "report": "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],report_name)}
    result_url = "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    if public:
        data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient('mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem')
        #for crontab
        db.forecast.public2.drop()
        db.forecast.public.save(data)
        db.forecast.public2.save(data)
    return result_url

@task()
def teco_spruce_forecast_cron2(pars,forecast_year,forecast_day,temperature_treatment=0.0,co2_treatment=380.0,da_task_id=None,public=None):
    """
        Forecasting
        args: pars - Initial parameters for TECO SPRUCE
              forecast_year,forecast_day

    """
    task_id = str(teco_spruce_forecast_cron2.request.id)
    resultDir = setup_result_directory(task_id)
    param_filename = create_template('SPRUCE_pars',pars,resultDir,check_params)
    #da_param_filename = create_template('SPRUCE_da_pars',pars,resultDir,check_params)
    da_param_filename ="SPRUCE_da_pars.txt"
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    #Set Param estimation file from DA
    if not da_task_id:
        try:
            copyfile("{0}/Paraest.txt".format(spruce_data_folder),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/SPRUCE_da_pars.txt".format(spruce_data_folder),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt or SPRUCE_da_pars.txt".format(spruce_data_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/input/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/ecopad_tasks2/{1}/input/SPRUCE_da_pars.txt".format(basedir,da_task_id),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/input/Paraest.txt or SPRUCE_da_pars.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}".format("/data/{0}".format(param_filename),
                                    "/spruce_data/SPRUCE_old_forcing.txt", "/spruce_data/SPRUCE_obs.txt",
                                    "/data",2, "/data/{0}".format(da_param_filename),
                                    "/spruce_data/Weathergenerate",forecast_year, forecast_day,
                                    temperature_treatment,co2_treatment)
    result = docker_task(docker_name="teco_spruce",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_forecast_viz.R {0} {1} {2} {3}".format("obs_file/SPRUCE_obs.txt","/data","/data",100)
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    # Yuanyuan add to reformat output data
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd = "Rscript reformat_to_csv.R {0} {1} {2} {3} {4}".format("/data","/data",100,temperature_treatment,co2_treatment)
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir) docker_cmd = "Rscript reformat_to_csv_backup.R {0} {1} {2}".format("/data","/data",100)
    # docker_opts = None docker_cmd = None
    result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP Forecast','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp_forecast.png'),
                'one_label':'ER Forecast','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er_forecast.png'),
                'two_label':'Foliage Forecast','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_forecast.png'),
                'three_label':'Wood Forecast','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood_forecast.png'),
                'four_label':'Root Forecast','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root_forecast.png'),
                'five_label':'Soil Forecast','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil_forecast.png')}
    report_data['title']="SPRUCE Ecological Forecast Task Report"
    desc = "Use constrained parameters from Data Assimilation to predict carbon fluxes and pool sizes. "
    desc = desc + "Forcing inputs are genereated by auto-regression model using historical climate data of the SPRUCE site. "
    desc = desc + "Allow users to choose which year and day to make predictations of ecosystem in response to treatment effects."
    report_data['description']=desc
    report_name = create_report('report',report_data,resultDir)
    #return {"data":"http://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id']),
    #        "report": "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],report_name)}
    result_url = "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    if public:
        data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient('mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem')
        #for crontab
        db.forecast.public.save(data)
        db.forecast.public2.save(data)
    return result_url

@task()
def teco_spruce_v2_0_simulation(pars): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
        to file, and store the file in input folder.
        call teco_spruce_model.
    """
    task_id = str(teco_spruce_v2_0_simulation.request.id)
    resultDir = setup_result_directory(task_id)
    #create param file
    param_filename = create_template('SPRUCE_v2_0_pars',pars,resultDir,check_params_v2_0)
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5}".format("/data/{0}".format(param_filename),"/spruce_data/SPRUCE_v2_0_forcing.txt",
                                    "/spruce_data/SPRUCE_v2_0_obs.txt",
                                    "/data", 0 , "/spruce_data/SPRUCE_v2_0_da_pars.txt")

    result = docker_task(docker_name="teco_spruce_v2_0",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    #Run R Plots #chang edited_060318
    os.makedirs("{0}/graphoutput".format(host_data_resultDir)) #make plot directory
    docker_opts = "-v {0}:/usr/local/src/myscripts/graphoutput:z ".format(host_data_resultDir)
    docker_cmd = None
    result = docker_task(docker_name="ecopad_r_v2_0",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    ##
    #Clean up result Directory
    clean_up_v2_0(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
                'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
                'two_label':'Foliage','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage.png'),
                'three_label':'Wood','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood.png'),
                'four_label':'Root','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                'five_label':'Soil','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
    report_data['title']="SPRUCE Ecological Simulation Task Report"
    report_data['description']="Simulations of carbon fluxes and pool sizes for SPRUCE experiment based on user defined initial parameters."

    report = create_report('report',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url

@task()
def teco_spruce_v2_0_data_assimilation(pars):
    """
        DA TECO Spruce
        args: pars - Initial parameters for TECO SPRUCE
        kwargs: da_params - Which DA variable and min and max range for 18 variables

    """
    task_id = str(teco_spruce_v2_0_data_assimilation.request.id)
    resultDir = setup_result_directory(task_id)
    #parm template file
    param_filename = create_template('SPRUCE_v2_0_pars',pars,resultDir,check_params_v2_0)
    da_param_filename = create_template('SPRUCE_v2_0_da_pars',pars,resultDir,check_params)
    #if da_params:
    #    da_param_filename = create_template('spruce_da_pars',da_params,resultDir,check_params)
    #else:
    #    copyfile("{0}/ecopad_tasks2/default/SPRUCE_da_pars.txt".format(basedir),"{0}/SPRUCE_da_pars.txt".format(resultDir))
    #    da_param_filename ="SPRUCE_da_pars.txt"
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5}".format("/data/{0}".format(param_filename),"/spruce_data/SPRUCE_v2_0_forcing.txt",
                                    "/spruce_data/SPRUCE_v2_0_obs.txt",
                                    "/data",1, "/data/{0}".format(da_param_filename))
    result = docker_task(docker_name="teco_spruce_v2_0",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_da_viz.R {0} {1}".format("/data/Paraest.txt","/data")
    result = docker_task(docker_name="ecopad_r_v2_0",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    report_data ={'zero_label':'Results','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'histogram.png')}
    report_data['title']="SPRUCE Ecological Data Assimilation Task Report"
    desc= "Multiple data streams from SPRUCE are assimilated to TECO model using MCMC algorithm. "\
            "The current dataset are mainly from pre-treatment measurement from 2011 to 2014. "\
            "This will be updated regularly when new data stream is available. 5 out of 18 parameters are constrained from pre-treatment data. "\
            "The 18 parameters are (1) specific leaf area, (2) maximum leaf growth rate, (3) maximum root growth rate, "\
            "(4) maximum stem growth rate, (5) maximum rate of carboxylation, (6) turnover rate of foliage pool, "\
            "(7) turnover rate of woody pool, (8) turnover rate of root pool, (9) turnover rate of fine litter pool, "\
            "(10) turnover rate of coarse litter pool, (11) turnover rate of fast soil pool, (12) turnover rate of slow soil pool, "\
            "(13) turnover rate of passive soil pool, (14) onset of growing degree days, (15) temperature sensitivity Q10, "\
            "(16) baseline leaf respiration, (17) baseline stem respiration, (18) baseline root respiration"
        
    report_data['description']=desc
    report_name = create_report('report_da',report_data,resultDir)
    return "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

@task()
def teco_SEV_simulation(pars): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
        to file, and store the file in input folder.
        call teco_spruce_model.
    """
    task_id = str(teco_SEV_simulation.request.id)
    resultDir = setup_result_directory(task_id)
    #create param file
    param_filename = create_template('SEV_pars2',pars,resultDir,check_params_SEV2)
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_sev_data="{0}/local/SEV_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/SEV_data:z".format(host_data_resultDir,host_data_dir_sev_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/SEV_obs_flux.txt",
                                    "/data/", 0 , "/SEV_data/Weathergenerate_SEV_met", 2027, 365, 0, 400, "/SEV_data/input")
    result = docker_task(docker_name="teco_sev",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url

@task()
def teco_SEV_data_assimilation(pars):
    """
        DA TECO SEV
        args: pars - Initial parameters for TECO_SEV
        kwargs: da_params - Which DA variable and min and max range for 18 variables

    """
    task_id = str(teco_SEV_data_assimilation.request.id)
    resultDir = setup_result_directory(task_id)
    #parm template file
    param_filename = create_template('SEV_pars2',pars,resultDir,check_params_SEV2)
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_sev_data="{0}/local/SEV_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_sev_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",1, "/SEV_data/Weathergenerate_SEV_met", 2027, 365, 0, 400, "/SEV_data/input")
    result = docker_task(docker_name="teco_sev",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    return "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

@task()	
def teco_SEV_forecast(pars,forecast_year,forecast_day,Mtreat=0,Vtreat=0,da_task_id=None,public=None):
    """
        Forecasting 
        args: pars - Initial parameters for TECO SEV
              forecast_year,forecast_day
		Mtreat: 
				decrease mean rainfall
		Vtreat: 
				change the coefficient of variation of rainfall
    """
    task_id = str(teco_SEV_forecast.request.id)
    resultDir = setup_result_directory(task_id)
    os.makedirs("{0}/plot".format(resultDir))
    param_filename = create_template('SEV_pars2',pars,resultDir,check_params_SEV2)
    #da_param_filename = create_template('SPRUCE_da_pars',pars,resultDir,check_params)
    da_param_filename ="SEV_da_pars.txt"
    host_data_dir_sev_data="{0}/local/SEV_data".format(host_data_dir)
    #Set Param estimation file from DA 
    if not da_task_id:
        try:
            copyfile("{0}/Paraest.txt".format(sev_data_folder),"{0}/Paraest.txt".format(resultDir))
            #copyfile("{0}/SEV_da_pars.txt".format(sev_data_folder),"{0}/SEV_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt or SEV_da_pars.txt".format(sev_data_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest.txt".format(resultDir))
            #copyfile("{0}/ecopad_tasks2/{1}/input/SEV_da_pars.txt".format(basedir,da_task_id),"{0}/SEV_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/input/Paraest.txt or SEV_da_pars.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)

    host_data_dir_spruce_data="{0}/local/SEV_data".format(host_data_dir)
    if Mtreat == 0 and Vtreat == 1:
        docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_spruce_data)
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",2, "/SEV_data/Weathergenerate_SEV_variance", forecast_year, forecast_day, "/SEV_data/input")
    elif Mtreat == 1 and Vtreat == 0:
        docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_spruce_data)
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",2, "/SEV_data/Weathergenerate_SEV_mean_25", forecast_year, forecast_day, "/SEV_data/input")
    elif Mtreat == 2 and Vtreat == 0:
        docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_spruce_data)
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",2, "/SEV_data/Weathergenerate_SEV_mean_50", forecast_year, forecast_day, "/SEV_data/input")
    elif Mtreat == 1 and Vtreat == 1:
        docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_spruce_data)
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",2, "/SEV_data/Weathergenerate_SEV_mean_25_variance", forecast_year, forecast_day, "/SEV_data/input")
    elif Mtreat == 2 and Vtreat == 1:
        docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_spruce_data)
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",2, "/SEV_data/Weathergenerate_SEV_mean_50_variance", forecast_year, forecast_day, "/SEV_data/input")
    elif Mtreat == 0 and Vtreat == 0:
        docker_opts = "-v {0}:/data:z -v {1}:/SEV_data".format(host_data_resultDir,host_data_dir_spruce_data)
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format("/data/{0}".format(param_filename),"/SEV_data/SEV_forcing_2010_2017.txt",
                                    "/SEV_data/obs_flux_gapfilled.txt",
                                    "/data/",2, "/SEV_data/Weathergenerate_SEV_met", forecast_year, forecast_day, "/SEV_data/input")

    
    result = docker_task(docker_name="teco_sev_gy_test",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    #Run R Plots(Yuan Gao modified)
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
	###########resume
    docker_cmd ="Rscript ECOPAD_forecast_viz.R {0} {1} {2} {3}".format("obs_file/SEV_obs_flux.txt","/data","/data",100)
    result = docker_task(docker_name="teco_rscript",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
   
    result_url = "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    if public:
        data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient("mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem",27017)
        db.forecast.public.sev.save(data)

    return result_url


@task()
def teco_spruce_forecast_past(pars,forecast_year,forecast_day,temperature_treatment=0.0,co2_treatment=380.0,da_task_id=None,public=None):
    """
        Forecasting 
        args: pars - Initial parameters for TECO SPRUCE
              forecast_year,forecast_day
    """
    task_id = str(teco_spruce_forecast_past.request.id)
    resultDir = setup_result_directory(task_id)
    param_filename = create_template('SPRUCE_pars',pars,resultDir,check_params)
    #da_param_filename = create_template('SPRUCE_da_pars',pars,resultDir,check_params)
    da_param_filename ="SPRUCE_da_pars.txt"
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    #Set Param estimation file from DA 
    if not da_task_id:
        try:
            copyfile("{0}/SPRUCE_forcing_p.txt".format(spruce_data_folder),"{0}/SPRUCE_forcing_p.txt".format(resultDir))
            copyfile("{0}/Paraest.txt".format(spruce_data_folder),"{0}/Paraest.txt".format(resultDir))
           # copyfile("{0}/Paraest.txt".format(spruce_data_folder),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/SPRUCE_da_pars.txt".format(spruce_data_folder),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt or SPRUCE_da_pars.txt".format(spruce_data_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/input/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest.txt".format(resultDir))
            copyfile("{0}/ecopad_tasks2/{1}/input/SPRUCE_da_pars.txt".format(basedir,da_task_id),"{0}/SPRUCE_da_pars.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/input/Paraest.txt or SPRUCE_da_pars.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}".format("/data/{0}".format(param_filename),
                                    "/spruce_data/SPRUCE_forcing_p.txt", "/spruce_data/SPRUCE_obs_2015.txt",
                                   # "/spruce_data/SPRUCE_forcing_p.txt", "/spruce_data/SPRUCE_obs.txt",
                                    "/data",2, "/data/{0}".format(da_param_filename),
                                    "/spruce_data/Weathergenerate",forecast_year, forecast_day,
                                    temperature_treatment,co2_treatment)
    result = docker_task(docker_name="teco_spruce",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd ="Rscript ECOPAD_forecast_viz.R {0} {1} {2} {3}".format("obs_file/SPRUCE_obs_2015.txt","/data","/data",100)
   # docker_cmd ="Rscript ECOPAD_forecast_viz.R {0} {1} {2} {3}".format("obs_file/SPRUCE_obs.txt","/data","/data",100)
    #result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    # Yuanyuan add to reformat output data
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv.R {0} {1} {2} {3} {4}".format("/data","/data",100,temperature_treatment,co2_treatment)
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv_backup.R {0} {1} {2}".format("/data","/data",100)
    # docker_opts = None
    # docker_cmd = None
    #result = docker_task(docker_name="ecopad_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    #Clean up result Directory
    clean_up(resultDir)
    #Create Report
    #report_data ={'zero_label':'GPP Forecast','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp_forecast.png'),
    #            'one_label':'ER Forecast','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er_forecast.png'),
    #            'two_label':'Foliage Forecast','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_forecast.png'),
    #            'three_label':'Wood Forecast','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood_forecast.png'),
    #            'four_label':'Root Forecast','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root_forecast.png'),
    #            'five_label':'Soil Forecast','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil_forecast.png')}
    #report_data['title']="SPRUCE Ecological Forecast Task Report"
    #desc = "Use constrained parameters from Data Assimilation to predict carbon fluxes and pool sizes. "
    #desc = desc + "Forcing inputs are genereated by auto-regression model using historical climate data of the SPRUCE site. "
    #desc = desc + "Allow users to choose which year and day to make predictations of ecosystem in response to treatment effects."
    #report_data['description']=desc
    #report_name = create_report('report',report_data,resultDir)
    #return {"data":"http://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id']),
    #        "report": "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],report_name)}
    result_url = "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    if public:
        data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient("mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem",27017)
        db.forecast.public2016.save(data)

    return result_url

#elm-Oak ridge	
@task()
def elm_spruce_simulation(): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
        to file, and store the file in input folder.
        call teco_spruce_model.
    """
    task_id = str(elm_spruce_simulation.request.id)
    resultDir = elm_setup_result_directory(task_id)
    #create param file
    #param_filename = create_template('SEV_pars',pars,resultDir,check_params_SEV)
    #Run elm code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_elm_data="{0}/local/elm_spruce_data".format(host_data_dir)
    docker_opts = "-v {0}/run:{1}:z -v {2}:/elm_spruce_data:z -h ubuntu".format(host_data_resultDir,results_elm,host_data_dir_elm_data)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("./site_fullrun.py", "--site US-SPR", "--cpl_bypass --nopftdyn --tstep 1",
										"--machine ubuntu --ccsm_input", "/elm_spruce_data/inputdata", "--model_root /home/ubuntu/E3SM",
										"--caseidprefix {0}".format(task_id), "--humhol")

    result = docker_task(docker_name="elm",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #clean_up_elm1(results_elm, resultDir)
    #move("mv -rf [0] /output/".format(results_elm))
    #clean_up_elm1(results_elm)

    #Plotting
    docker_opts = "-v {0}/plot:{1}:z -v {2}/run:/run:z -h ubuntu".format(host_data_resultDir,results_elm_plot,host_data_resultDir) 
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("./plotcase.py", "--case {0}".format(task_id), "--site US-SPR", "--compset ICB20TRCNPRDCTCBC",
										"--ystart 2013 --yend 2019", "--vars GPP,ER,NEE,WOODC,LEAFC,SOILC", "--avpd 30", "--csmdir /run --pdf")
    #docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("./plotcase.py", "--case {0}".format(task_id), "--site US-SPR", "--compset ICB20TRCNPRDCTCBC",
	#									"--ystart 2000 --yend 2014", "--vars GPP,ER,NEE,WOODC,LEAFC,SOILC", "--avpd 30", "--csmdir /run --pdf")
    result = docker_task(docker_name="elm",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    clean_up_elm1(resultDir)
    #clean_up_elm2(task_id)
    #os.system("mv -rf /plots/[0]/daily /plot/".format(task_id))
   
	##
    #Clean up result Directory
    #clean_up_SEV(resultDir)
    #Create Report
    #report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
     #           'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
      #          'two_label':'NEE','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'nee.png'),
       #         'three_label':'ANPP','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_NPP.png')}
                #'four_label':'Root','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                #'five_label':'Soil','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
    #report_data['title']="SEV Ecological Simulation Task Report"
    #report_data['description']="Simulations of carbon fluxes for SEV experiment based on user defined initial parameters."

    #report = create_report('report_sev',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url

@task()
def elm_spruce_simulation_plot(): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
        to file, and store the file in input folder.
        call teco_spruce_model.
    """
    task_id = str("267ffcac-9138-4a23-90c2-27236a23bd39")
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    #resultDir = elm_setup_result_directory(task_id)
    #create param file
    #param_filename = create_template('SEV_pars',pars,resultDir,check_params_SEV)
    #Run elm code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_elm_data="{0}/local/elm_spruce_data".format(host_data_dir)
    # docker_opts = "-v {0}:{1}:z -v {2}:/elm_spruce_data:z -h ubuntu".format(host_data_resultDir,results_elm,host_data_dir_elm_data)
    # docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("./site_fullrun.py", "--site US-SPR", "--cpl_bypass --nopftdyn --tstep 1",
										# "--machine ubuntu --ccsm_input", "/elm_spruce_data/inputdata", "--model_root /home/ubuntu/E3SM",
										# "--caseidprefix {0}".format(task_id), "--humhol")

    # result = docker_task(docker_name="elm",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #clean_up_elm1(results_elm, resultDir)
    #move("mv -rf [0] /output/".format(results_elm))
    #clean_up_elm1(results_elm)

#    #Plotting
    docker_opts = "-v {0}/plot:/plots:z -v {2}/run:/run:z -v {2}/results:/results:z -h ubuntu".format(host_data_resultDir,results_elm_plot,host_data_resultDir) 
    docker_cmd = "{0} {1} {2} {3}".format("./getvar.py", "--case {0}".format(task_id), "--site US-SPR", "--vars GPP,ER,NEE,WOODC,LEAFC,SOILC")
#
#    #docker_opts = "-v {0}/plot:{1}:z -v {2}/run:/run:z -v {2}/results:/results:z -h ubuntu".format(host_data_resultDir,results_elm_plot,host_data_resultDir) 
#    #docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("./plotcase.py", "--case {0}".format(task_id), "--site US-SPR", "--compset ICB20TRCNPRDCTCBC",
##										"--ystart 2000 --yend 2014", "--vars GPP,ER,NEE,WOODC,LEAFC,SOILC", "--avpd 1", "--csmdir /run --pdf")
    result = docker_task(docker_name="elm",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    # Yuanyuan add to reformat output data
    docker_opts = "-v {0}/results:/results:z -h ubuntu".format(host_data_resultDir)
    docker_cmd = "Rscript reformat_to_csv.R {0} {0}".format("/results")
    result = docker_task(docker_name="elm",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
#    if not os.path.exists("{0}/forecast_csv/ecopad_elm".format(basedir)):
#        os.makedirs("{0}/forecast_csv/ecopad_elm".format(basedir))

    # method 1
    #command_flag=True
    #if command_flag:
    #    ecopad_elm_datadir = "{0}/forecast_csv/ecopad_elm".format(basedir)
    #    docker_opts = "-v {0}/results:/results:z -v {1}:/ecopad_elm:z ".format(host_data_resultDir,ecopad_elm_datadir)
    #    docker_cmd = "Rscript reformat_to_csv.R {0} {1}".format("/results","/ecopad_elm")
    #    result = docker_task(docker_name="elm",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    # method 2
    #resultDir="{0}/results".format(host_data_resultDir)
    clean_up_elm1(resultDir)
    print resultDir
    #clean_up_elm1(resultDir)
    #move("/{0}/forecasting/".format(resultDir), "/data/static/forecast_csv/ecopad_elm/")
    #move("{0}/*.csv".format(resultDir),"{0}/forecast_csv/ecopad_elm/*.csv".format(basedir))
    # method 3  
#    try: 
#        for mvfile in glob("{0}/forecasting/*.csv".format(host_data_resultDir)):
#            head,tail=os.path.split(mvfile)
#            dst_file=os.path.join("{0}/forecast_csv/ecopad_elm/{1}".format(basedir,tail))
#            i=1 
#            if os.path.exists(dst_file):
#                with open(dst_file, 'a') as singleFile:
#                    for line in open(mvfile, 'r'):
#                       if i > 1:
#                          singleFile.write(line)          
#                       i=2
#                os.remove(mvfile)
#            else: 
#            #move(mvfile,"{0}/forecast_csv/{1}".format(basedir,current_date))
#                move(mvfile,"{0}/forecast_csv/ecopad_elm/".format(basedir)) 
#    except:
#        pass 
#

    ##clean_up_elm2(task_id)
    #os.system("mv -rf /plots/[0]/daily /plot/".format(task_id))
   
	##
    #Clean up result Directory
    #clean_up_SEV(resultDir)
    #Create Report
    #report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
     #           'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
      #          'two_label':'NEE','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'nee.png'),
       #         'three_label':'ANPP','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_NPP.png')}
                #'four_label':'Root','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                #'five_label':'Soil','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
    #report_data['title']="SEV Ecological Simulation Task Report"
    #report_data['description']="Simulations of carbon fluxes for SEV experiment based on user defined initial parameters."

    #report = create_report('report_sev',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url

##for 2019 workshop
@task()
def teco_spruce_simulation_ws(pars): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
	to file, and store the file in input folder.
	call teco_spruce_model.
    """
    task_id = str(teco_spruce_simulation_ws.request.id)
    resultDir = setup_result_directory_ws(task_id)
    #create param file 
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    #Run Spruce TECO code 
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)	
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /{0}/SPRUCE_forcing_2011_2016.txt".format("spruce_data_ws", "teco_workshop_simul.nml")
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    #os.makedirs("{0}/graphoutput".format(host_data_resultDir)) #make plot directory
    docker_opts = "-v {0}:/usr/local/src/myscripts/graphoutput:z ".format(host_data_resultDir)
    docker_cmd = None
    result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
   

    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
                'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
                'two_label':'Foliage','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage.png'),
                'three_label':'Wood','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood.png'),
                'four_label':'Root','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                'five_label':'Soil','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
    report_data['title']="SPRUCE Ecological Simulation Task Report"
    report_data['description']="Simulations of carbon fluxes and pool sizes for SPRUCE experiment based on user defined initial parameters."

    report = create_report('report',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url

@task()
def teco_spruce_simulation_ws_custom(pars,forcing_file): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
	to file, and store the file in input folder.
	call teco_spruce_model.
    """
    task_id = str(teco_spruce_simulation_ws_custom.request.id)
    resultDir = setup_result_directory_ws(task_id)
    forcing_input = "{0}/{1}.txt".format(resultDir,forcing_file)
	#move custom forcing file
    move("{0}/{1}.txt".format(forcing_data_folder,forcing_file),forcing_input)
    #create param file 
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    #Run Spruce TECO code 
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)	
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws:z -v {1}:/spruce_data_ws:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /data/{2}.txt".format("spruce_data_ws", "teco_workshop_simul.nml", forcing_file)
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    #os.makedirs("{0}/graphoutput".format(host_data_resultDir)) #make plot directory
    docker_opts = "-v {0}:/usr/local/src/myscripts/graphoutput:z ".format(host_data_resultDir)
    docker_cmd = docker_cmd ="Rscript ECOPAD_viz_custom.R"
    result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
   

    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
                'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
                'two_label':'Foliage','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage.png'),
                'three_label':'Wood','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood.png'),
                'four_label':'Root','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                'five_label':'Soil','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
    report_data['title']="SPRUCE Ecological Simulation Task Report"
    report_data['description']="Simulations of carbon fluxes and pool sizes for SPRUCE experiment based on user defined initial parameters."

    report = create_report('report',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url	

@task()
def teco_spruce_data_assimilation_ws_custom(pars,forcing_file):
    """
        DA TECO Spruce
        args: pars - Initial parameters for TECO SPRUCE
        kwargs: da_params - Which DA variable and min and max range for 18 variables

    """
    task_id = str(teco_spruce_data_assimilation_ws_custom.request.id)
    resultDir = setup_result_directory_ws(task_id)
    forcing_input = "{0}/{1}.txt".format(resultDir,forcing_file)
	#move custom forcing file
    move("{0}/{1}.txt".format(forcing_data_folder,forcing_file),forcing_input)
    #parm template file
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    da_param_filename = create_template('SPRUCE_da_pars_c',pars,resultDir,check_params_ws)
    #if da_params:
    #    da_param_filename = create_template('spruce_da_pars',da_params,resultDir,check_params)
    #else:
    #    copyfile("{0}/ecopad_tasks2/default/SPRUCE_da_pars.txt".format(basedir),"{0}/SPRUCE_da_pars.txt".format(resultDir))
    #    da_param_filename ="SPRUCE_da_pars.txt"
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws:z -v {1}:/spruce_data_ws:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /data/{2}.txt /{0}/{3} /{0}/{4}".format("spruce_data_ws", "teco_workshop_DA.nml", forcing_file, "cflux.txt", "cpool.txt")
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_da_viz.R {0} {1}".format("/data/Paraest.txt","/data")
    result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'Results','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'histogram.png')}
    report_data['title']="SPRUCE Ecological Data Assimilation Task Report"
    desc= "Multiple data streams from SPRUCE are assimilated to TECO model using MCMC algorithm. "\
            "The current dataset are mainly from pre-treatment measurement from 2011 to 2014. "\
            "This will be updated regularly when new data stream is available. 5 out of 18 parameters are constrained from pre-treatment data. "\
            "The 18 parameters are (1) specific leaf area, (2) maximum leaf growth rate, (3) maximum root growth rate, "\
            "(4) maximum stem growth rate, (5) maximum rate of carboxylation, (6) turnover rate of foliage pool, "\
            "(7) turnover rate of woody pool, (8) turnover rate of root pool, (9) turnover rate of fine litter pool, "\
            "(10) turnover rate of coarse litter pool, (11) turnover rate of fast soil pool, (12) turnover rate of slow soil pool, "\
            "(13) turnover rate of passive soil pool, (14) onset of growing degree days, (15) temperature sensitivity Q10, "\
            "(16) baseline leaf respiration, (17) baseline stem respiration, (18) baseline root respiration"
        
    report_data['description']=desc
    report_name = create_report('report_da',report_data,resultDir)
    return "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

@task()
def teco_spruce_simulation_ws_custom_grass(pars,forcing_file): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
	to file, and store the file in input folder.
	call teco_spruce_model.
    """
    task_id = str(teco_spruce_simulation_ws_custom_grass.request.id)
    resultDir = setup_result_directory_ws(task_id)
    forcing_input = "{0}/{1}.txt".format(resultDir,forcing_file)
	#move custom forcing file
    move("{0}/{1}.txt".format(forcing_data_folder,forcing_file),forcing_input)
    #create param file 
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    #Run Spruce TECO code 
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)	
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws:z -v {1}:/spruce_data_ws:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /data/{2}.txt".format("spruce_data_ws", "teco_workshop_simul_grass.nml", forcing_file)
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    #os.makedirs("{0}/graphoutput".format(host_data_resultDir)) #make plot directory
    docker_opts = "-v {0}:/usr/local/src/myscripts/graphoutput:z ".format(host_data_resultDir)
    docker_cmd = docker_cmd = docker_cmd ="Rscript ECOPAD_viz_custom_grass.R"
    result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
   

    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp.png'),
                'one_label':'ER','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er.png'),
                'two_label':'Foliage','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage.png'),
                'three_label':'Root','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root.png'),
                'four_label':'Soil','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil.png')}
           
    report_data['title']="SPRUCE Ecological Simulation Task Report"
    report_data['description']="Simulations of carbon fluxes and pool sizes for SPRUCE experiment based on user defined initial parameters."

    report = create_report('report_custom',report_data,resultDir)
    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    #report_url = "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],"report.htm")
    #{"report":report_url,"data":result_url}
    return result_url	

@task()
def teco_spruce_data_assimilation_ws_custom_grass(pars,forcing_file):
    """
        DA TECO Spruce
        args: pars - Initial parameters for TECO SPRUCE
        kwargs: da_params - Which DA variable and min and max range for 18 variables

    """
    task_id = str(teco_spruce_data_assimilation_ws_custom_grass.request.id)
    resultDir = setup_result_directory_ws(task_id)
    forcing_input = "{0}/{1}.txt".format(resultDir,forcing_file)
	#move custom forcing file
    move("{0}/{1}.txt".format(forcing_data_folder,forcing_file),forcing_input)
    #parm template file
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    da_param_filename = create_template('SPRUCE_da_pars_c',pars,resultDir,check_params_ws)
    #if da_params:
    #    da_param_filename = create_template('spruce_da_pars',da_params,resultDir,check_params)
    #else:
    #    copyfile("{0}/ecopad_tasks2/default/SPRUCE_da_pars.txt".format(basedir),"{0}/SPRUCE_da_pars.txt".format(resultDir))
    #    da_param_filename ="SPRUCE_da_pars.txt"
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws:z -v {1}:/spruce_data_ws:z".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /data/{2}.txt /{0}/{3} /{0}/{4}".format("spruce_data_ws", "teco_workshop_DA_grass.nml", forcing_file, "cflux.txt", "cpool.txt")
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_da_viz.R {0} {1}".format("/data/Paraest.txt","/data")
    result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'Results','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'histogram.png')}
    report_data['title']="SPRUCE Ecological Data Assimilation Task Report"
    desc= "Multiple data streams from a custom site are assimilated to TECO model using MCMC algorithm. "\
            
    report_data['description']=desc
    report_name = create_report('report_da',report_data,resultDir)
    return "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
		
@task()
def teco_spruce_data_assimilation_ws(pars):
    """
        DA TECO Spruce
        args: pars - Initial parameters for TECO SPRUCE
        kwargs: da_params - Which DA variable and min and max range for 18 variables

    """
    task_id = str(teco_spruce_data_assimilation_ws.request.id)
    resultDir = setup_result_directory_ws(task_id)
    #parm template file
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    da_param_filename = create_template('SPRUCE_da_pars_c',pars,resultDir,check_params_ws)
    #if da_params:
    #    da_param_filename = create_template('spruce_da_pars',da_params,resultDir,check_params)
    #else:
    #    copyfile("{0}/ecopad_tasks2/default/SPRUCE_da_pars.txt".format(basedir),"{0}/SPRUCE_da_pars.txt".format(resultDir))
    #    da_param_filename ="SPRUCE_da_pars.txt"
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /{0}/SPRUCE_forcing_2011_2016.txt /{0}/{2} /{0}/{3}".format("spruce_data_ws", "teco_workshop_DA.nml", "cflux.txt", "cpool.txt")
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    docker_cmd ="Rscript ECOPAD_da_viz.R {0} {1}".format("/data/Paraest.txt","/data")
    result = docker_task(docker_name="teco_spruce_workshop_v2_2_viz",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'Results','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'histogram.png')}
    report_data['title']="SPRUCE Ecological Data Assimilation Task Report"
    desc= "Multiple data streams from SPRUCE are assimilated to TECO model using MCMC algorithm. "\
            "The current dataset are from 2011 to 2016. "\
            "This will be updated regularly when new data stream is available. 5 out of 18 parameters are constrained. "\
            "The 18 parameters are (1) specific leaf area, (2) maximum leaf growth rate, (3) maximum root growth rate, "\
            "(4) maximum stem growth rate, (5) maximum rate of carboxylation, (6) turnover rate of foliage pool, "\
            "(7) turnover rate of woody pool, (8) turnover rate of root pool, (9) turnover rate of fine litter pool, "\
            "(10) turnover rate of coarse litter pool, (11) turnover rate of fast soil pool, (12) turnover rate of slow soil pool, "\
            "(13) turnover rate of passive soil pool, (14) onset of growing degree days, (15) temperature sensitivity Q10, "\
            "(16) baseline leaf respiration, (17) baseline stem respiration, (18) baseline root respiration"
        
    report_data['description']=desc
    report_name = create_report('report_da',report_data,resultDir)
    return "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

@task()
def teco_spruce_forecast_ws(pars,forecast_year,forecast_day,temperature_treatment=0.0,co2_treatment=380.0,da_task_id=None,public=None):
    """
        Forecasting 
        args: pars - Initial parameters for TECO SPRUCE
              forecast_year,forecast_day
    """
    task_id = str(teco_spruce_forecast_ws.request.id)
    resultDir = setup_result_directory_ws(task_id)
    #parm template file
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    da_param_filename = create_template('SPRUCE_da_pars_c',pars,resultDir,check_params_ws)
    #Set Param estimation file from DA 
    if not da_task_id:
        try:
            copyfile("{0}/Paraest.txt".format(spruce_data_ws_folder),"{0}/Paraest_example.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt".format(spruce_data_ws_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/output/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest_example.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/output/Paraest.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws".format(host_data_resultDir,host_data_dir_spruce_data)
    docker_cmd = "/{0}/{1} /{0}/SPRUCE_forcing_2011_2024.txt /{0}/cflux.txt /{0}/cpool.txt {2} {3}".format("spruce_data_ws", "teco_workshop_forecast.nml", temperature_treatment, co2_treatment)
    result = docker_task(docker_name="teco_spruce_ws",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    #Run R Plots
    docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
	###########resume
    docker_cmd ="Rscript ECOPAD_forecast_viz.R {0}".format("/data")
    result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    # Yuanyuan add to reformat output data
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv.R {0} {1} {2} {3} {4}".format("/data","/data",100,temperature_treatment,co2_treatment)
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv_backup.R {0} {1} {2}".format("/data","/data",100)
    # docker_opts = None
    # docker_cmd = None
    #result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    report_data ={'zero_label':'GPP Forecast','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp_forecast.png'),
                'one_label':'ER Forecast','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er_forecast.png'),
                'two_label':'Foliage Forecast','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_forecast.png'),
                'three_label':'Wood Forecast','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood_forecast.png'),
                'four_label':'Root Forecast','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root_forecast.png'),
                'five_label':'Soil Forecast','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil_forecast.png')}
    report_data['title']="SPRUCE Ecological Forecast Task Report"
    desc = "Use constrained parameters from Data Assimilation to predict carbon fluxes and pool sizes. "
    desc = desc + "Forcing inputs are genereated by auto-regression model using historical climate data of the SPRUCE site. "
    desc = desc + "Allow users to choose which year and day to make predictations of ecosystem in response to treatment effects."
    report_data['description']=desc
    report_name = create_report('report',report_data,resultDir)
    #return {"data":"http://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id']),
    #        "report": "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],report_name)}
    result_url = "https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    if public:
        data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient("mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem",27017)
        db.forecast.public_SPRUCE_ws.save(data)

    zip_folder(task_id)

    return result_url

@task()
def teco_spruce_ws_2020_simulation_changed_parameters(pars): # ,model_type="0", da_params=None):
    """ Setup task convert parameters from html portal
        to file, and store the file in input folder.
        call teco_spruce_model.
    """
    task_id = str(teco_spruce_ws_2020_simulation_changed_parameters.request.id)
    resultDir = setup_result_directory_ws_2020_default(task_id)
    #create param file
    param_filename = create_template('SPRUCE_workshop_2020',pars,resultDir + "/input",check_params_ws_2020)
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_SPRUCE_workshop_2020="{0}/local/spruce_data_ws_2020".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data:z".format(host_data_resultDir,host_data_dir_SPRUCE_workshop_2020)
    docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("/spruce_data/workshop_nml/teco_workshop_simu.nml","/data/input/{0}".format(param_filename),"/spruce_data/input/SPRUCE_da_pars.txt",
                                    "/spruce_data/input/SPRUCE_forcing_2011_2016.txt",
                                    "/data/output/SPRUCE", "/spruce_data/input/SPRUCE_cflux.txt", "/spruce_data/input/SPRUCE_cpool.txt",
                                    "/spruce_data/input/SPRUCE_ch4flux.txt")
    result = docker_task(docker_name="teco_spruce_2.3",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    rename_par_file(task_id)
    zip_folder(task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    return result_url

@task
def teco_spruce_ws_2020_da_changed_parameters(pars, use_cflux=0, use_cpool=0):
    task_id = str(teco_spruce_ws_2020_da_changed_parameters.request.id)
    resultDir = setup_result_directory_ws_2020_default(task_id)
    #create param file
    param_filename = create_template('SPRUCE_workshop_2020',pars,resultDir + "/input",check_params_ws_2020)
    da_param_filename = create_template('SPRUCE_workshop_2020_da',pars,resultDir + "/input",check_params_ws_2020)
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_SPRUCE_workshop_2020="{0}/local/spruce_data_ws_2020".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data:z".format(host_data_resultDir,host_data_dir_SPRUCE_workshop_2020)

    
    if use_cflux == 0 and use_cpool == 0:
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("/spruce_data/workshop_nml/teco_workshop_da_no_obs.nml","/data/input/{0}".format(param_filename),"/data/input/{0}".format(da_param_filename),
                                        "/spruce_data/input/SPRUCE_forcing_2011_2016.txt",
                                        "/data/output/SPRUCE", "/spruce_data/input/SPRUCE_cflux.txt", "/spruce_data/input/SPRUCE_cpool.txt",
                                        "/spruce_data/input/SPRUCE_ch4flux.txt")
        result = docker_task(docker_name="teco_spruce_2.3",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    if use_cflux == 1 and use_cpool == 0:
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("/spruce_data/workshop_nml/teco_workshop_da_cflux.nml","/data/input/{0}".format(param_filename),"/data/input/{0}".format(da_param_filename),
                                        "/spruce_data/input/SPRUCE_forcing_2011_2016.txt",
                                        "/data/output/DA_cflux/", "/spruce_data/input/SPRUCE_cflux.txt", "/spruce_data/input/SPRUCE_cpool.txt",
                                        "/spruce_data/input/SPRUCE_ch4flux.txt")
        result = docker_task(docker_name="teco_spruce_2.3",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    if use_cflux == 0 and use_cpool == 1:
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("/spruce_data/workshop_nml/teco_workshop_da_cpool.nml","/data/input/{0}".format(param_filename),"/data/input/{0}".format(da_param_filename),
                                        "/spruce_data/input/SPRUCE_forcing_2011_2016.txt",
                                        "/data/output/DA_cpool/", "/spruce_data/input/SPRUCE_cflux.txt", "/spruce_data/input/SPRUCE_cpool.txt",
                                        "/spruce_data/input/SPRUCE_ch4flux.txt")
        result = docker_task(docker_name="teco_spruce_2.3",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    if use_cflux == 1 and use_cpool == 1:
        docker_cmd = "{0} {1} {2} {3} {4} {5} {6} {7}".format("/spruce_data/workshop_nml/teco_workshop_da_cflux_cpool.nml","/data/input/{0}".format(param_filename),"/data/input/{0}".format(da_param_filename),
                                        "/spruce_data/input/SPRUCE_forcing_2011_2016.txt",
                                        "/data/output/DA_cpool_cflux/", "/spruce_data/input/SPRUCE_cflux.txt", "/spruce_data/input/SPRUCE_cpool.txt",
                                        "/spruce_data/input/SPRUCE_ch4flux.txt")
        result = docker_task(docker_name="teco_spruce_2.3",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    # docker_cmd ="Rscript R_code_for_DA_Unit_8.R {0} {1} {2} ".format(3, "/data", "/spruce_data")
    # result = docker_task(docker_name="teco_workshop_2020_viz",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    # spruce_ws_data_folder="/data/local/spruce_data_ws_2020"
    # copyfile("{0}/show_images/index_DA_with_cpool_vs_cflux.html".format(spruce_ws_data_folder),"{0}/report.html".format(resultDir))

    rename_par_file(task_id)
    rename_da_file(task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])
    return result_url

@task()
def teco_spruce_ws_2020_forecast(pars,forecast_year,forecast_day,temperature_treatment=0.0,co2_treatment=380.0,rep_n=100,da_task_id=None,public=None):
    """
        Forecasting 
        args: pars - Initial parameters for TECO SPRUCE
              forecast_year,forecast_day
    """
    task_id = str(teco_spruce_ws_2020_forecast.request.id)
    resultDir = setup_result_directory_ws(task_id)
    #parm template file
    param_filename = create_template('SPRUCE_pars_ws',pars,resultDir,check_params_ws)
    da_param_filename = create_template('SPRUCE_da_pars_c',pars,resultDir,check_params_ws)
    #Set Param estimation file from DA 
    if not da_task_id:
        try:
            copyfile("{0}/Paraest.txt".format(spruce_data_ws_folder),"{0}/Paraest_example.txt".format(resultDir))
        except:
            error_file = "{0}/Paraest.txt".format(spruce_data_ws_folder)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    else:
        try:
            copyfile("{0}/ecopad_tasks2/{1}/output/Paraest.txt".format(basedir,da_task_id),"{0}/Paraest_example.txt".format(resultDir))
        except:
            error_file = "{0}/ecopad_tasks2/{1}/output/Paraest.txt".format(basedir,da_task_id)
            raise Exception("Parameter Estimation file location problem. {0} file not found.".format(error_file))
    #Run Spruce TECO code
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_spruce_data="{0}/local/spruce_data_ws".format(host_data_dir)
    host_data_dir_spruce_data_2020="{0}/local/spruce_data_ws_2020_forecast".format(host_data_dir)
    docker_opts = "-v {0}:/data:z -v {1}:/spruce_data_ws -v {2}:/spruce_data_ws_2020_forecast".format(host_data_resultDir,host_data_dir_spruce_data, host_data_dir_spruce_data_2020)

    for num in range(1, int(rep_n) + 1):
        docker_cmd = "/{0}/{1} /{6}/weathergenerate/EMforcing{7}.csv /{0}/cflux.txt /{0}/cpool.txt {2} {3} {4} {5}".format("spruce_data_ws", "teco_workshop_forecast.nml", temperature_treatment, co2_treatment, 1, num, "spruce_data_ws_2020_forecast", str(num).zfill(3))
        result = docker_task(docker_name="teco_workshop_2020_forecast",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    #Run R Plots
    if int(rep_n) == 100:
        docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
        ###########resume
        docker_cmd ="Rscript ECOPAD_forecast_viz.R {0}".format("/data")
        result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    # Yuanyuan add to reformat output data
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv.R {0} {1} {2} {3} {4}".format("/data","/data",100,temperature_treatment,co2_treatment)
    #docker_opts = "-v {0}:/data:z ".format(host_data_resultDir)
    #docker_cmd = "Rscript reformat_to_csv_backup.R {0} {1} {2}".format("/data","/data",100)
    # docker_opts = None
    # docker_cmd = None
    #result = docker_task(docker_name="ecopad_r_v2_2",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    
    #Clean up result Directory
    clean_up_v2_2(resultDir)
    #Create Report
    if int(rep_n) == 100:
        report_data ={'zero_label':'GPP Forecast','zero_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'gpp_forecast.png'),
                    'one_label':'ER Forecast','one_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'er_forecast.png'),
                    'two_label':'Foliage Forecast','two_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'foliage_forecast.png'),
                    'three_label':'Wood Forecast','three_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'wood_forecast.png'),
                    'four_label':'Root Forecast','four_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'root_forecast.png'),
                    'five_label':'Soil Forecast','five_url':'/ecopad_tasks2/{0}/plot/{1}'.format(task_id,'soil_forecast.png')}
        report_data['title']="SPRUCE Ecological Forecast Task Report"
        desc = "Use constrained parameters from Data Assimilation to predict carbon fluxes and pool sizes. "
        desc = desc + "Forcing inputs are genereated by auto-regression model using historical climate data of the SPRUCE site. "
        desc = desc + "Allow users to choose which year and day to make predictations of ecosystem in response to treatment effects."
        report_data['description']=desc
        report_name = create_report('report',report_data,resultDir)
        #return {"data":"http://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id']),
        #        "report": "http://{0}/ecopad_tasks2/{1}/{2}".format(result['host'],result['task_id'],report_name)}
    result_url = "https://ecolab.nau.edu/ecopad_tasks2/{0}".format(task_id)

    zip_folder(task_id)
    # if public:
    #     data={'tag':public,'result_url':result_url,'task_id':task_id,'timestamp':datetime.now()}
    #     db=MongoClient("mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem",27017)
    #     db.forecast.public_SPRUCE_ws.save(data)
    return result_url
	
@task()
def proda_task1():
    task_id = str(proda_task1.request.id)
    resultDir = setup_result_directory(task_id)
    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_proda_data="{0}/local/proda_data".format(host_data_dir)

    docker_opts = "-v {0}:/data:z -v {1}:/proda_data:z".format(host_data_resultDir,host_data_dir_proda_data)

    docker_cmd = "python nn_clm_cen.py /proda_data/ /data/ 1"
    result = docker_task(docker_name="proda_2020",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript NN_Indi_MAP_Project_CLM_CEN.R 1 /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript nn_para_map.R /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

    zip_folder(task_id)

    return result_url

@task()
def proda_task2(is_default_setting, nn_loss, nn_optimizer, nn_batch_size, nn_epochs, nn_layer, nn_layer_num, nn_drop_ratio, nn_activation):
    task_id = str(proda_task2.request.id)
    resultDir = setup_result_directory(task_id)

    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_proda_data="{0}/local/proda_data".format(host_data_dir)

    docker_opts = "-v {0}:/data:z -v {1}:/proda_data:z".format(host_data_resultDir,host_data_dir_proda_data)

    docker_cmd = "python nn_clm_cen.py /proda_data/ /data/ {0} {1} {2} {3} {4} {5} {6} {7} {8}".format(is_default_setting, nn_loss, nn_optimizer, nn_batch_size, nn_epochs, nn_layer, nn_layer_num, nn_drop_ratio, nn_activation)
    result = docker_task(docker_name="proda_2020",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript NN_Indi_MAP_Project_CLM_CEN.R 1 /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript nn_para_map.R /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

    zip_folder(task_id)

    return result_url

@task()
def proda_task3():
    task_id = str(proda_task3.request.id)
    resultDir = setup_result_directory(task_id)

    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_proda_data="{0}/local/proda_data".format(host_data_dir)

    docker_opts = "-v {0}:/data:z -v {1}:/proda_data:z".format(host_data_resultDir,host_data_dir_proda_data)

    docker_cmd = "Rscript One_Batch_DA.R /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

    zip_folder(task_id)

    return result_url

@task()
def proda_task4(nn_task_id, one_batch_task_id):
    task_id = str(proda_task4.request.id)
    resultDir = setup_result_directory(task_id)

    nn_result_dir = "{0}/static/ecopad_tasks2/{1}".format("/data", nn_task_id)
    one_batch_result_dir = "{0}/static/ecopad_tasks2/{1}".format("/data", one_batch_task_id)

    host_data_resultDir = "{0}/static/ecopad_tasks2/{1}".format(host_data_dir,task_id)
    host_data_dir_proda_data="{0}/local/proda_data".format(host_data_dir)

    copy_task_result(nn_result_dir + "/output_data", resultDir + "/output_data")
    copy_task_result(one_batch_result_dir + "/output_data", resultDir + "/output_data")

    docker_opts = "-v {0}:/data:z -v {1}:/proda_data:z".format(host_data_resultDir,host_data_dir_proda_data)

    docker_cmd = "Rscript NN_Indi_MAP_Project_CLM_CEN.R 1 /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript NN_Indi_MAP_Project_CLM_CEN.R 2 /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript Global_Projection_NN_CLM_CEN.R 0 /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript Global_Projection_NN_CLM_CEN.R 1 /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript Different_Method_obs_vs_mod.R /proda_data/ /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    docker_cmd = "Rscript different_method_soil_map.R /data/"
    result = docker_task(docker_name="test_proda_2020_r",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    result_url ="https://{0}/ecopad_tasks2/{1}".format(result['host'],result['task_id'])

    zip_folder(task_id)

    return result_url

@task()
def teco_sev_ef():
    task_id = str(teco_sev_ef.request.id)
    resultDir = setup_result_directory(task_id)

    os.makedirs("{0}/plot".format(resultDir))

    s = ["black_control", "black_dry_average", "black_dry_extreme", "black_dry_extreme_dry_average", "black_wet_extreme", "black_wet_extreme_dry_average",
            "blue_control", "blue_dry_average", "blue_dry_extreme", "blue_dry_extreme_dry_average", "blue_wet_extreme", "blue_wet_extreme_dry_average",
        ]

    for ss in s:
        os.makedirs("{0}/plot/{1}".format(resultDir, ss))

    host_data_dir_data="{0}/local/TECO_SEV_2021".format(host_data_dir)
    docker_opts = "-v {0}:/SEV_data:z".format(host_data_dir_data)
    docker_cmd = "python3 download_data.py"
    result = docker_task(docker_name="teco_sev_2021",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    for i in range(1, 31):
        docker_cmd = "./TECO.exe /SEV_data/hpcnml/black_plot{0}_da.nml".format(str(i))
        result = docker_task(docker_name="teco_sev_2021",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
        docker_cmd = "./TECO.exe /SEV_data/hpcnml/blue_plot{0}_da.nml".format(str(i))
        result = docker_task(docker_name="teco_sev_2021",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)
    docker_cmd = "Rscript ECOPAD_forecast_viz.R test /SEV_data /SEV_data 500"
    result = docker_task(docker_name="teco_sev_2021",docker_opts=docker_opts,docker_command=docker_cmd,id=task_id)

    for ss in s:
        copy_task_result("/data/local/TECO_SEV_2021/figures/{0}".format(ss), resultDir+"/plot/{0}".format(ss))

    result_url = "https://{0}/ecopad_tasks2/{1}/plot/".format(result['host'],result['task_id'])
    
    publics = ["EM1_FORECAST_0_0", "EM1_FORECAST_1_0", "EM1_FORECAST_2_0", "EM1_FORECAST_3_0", "EM1_FORECAST_4_0", "EM1_FORECAST_5_0", 
                "EM1_FORECAST_0_1", "EM1_FORECAST_1_1", "EM1_FORECAST_2_1", "EM1_FORECAST_3_1", "EM1_FORECAST_4_1", "EM1_FORECAST_5_1", 
    ]

    for i in range(0, len(publics)):
        data={'tag':publics[i],'result_url':result_url+s[i],'task_id':task_id,'timestamp':datetime.now()}
        db=MongoClient("mongodb://quser:qpass@cybercom_mongo:27017/?ssl=true&ssl_ca_certs=/ssl/testca/cacert.pem&ssl_certfile=/ssl/client/mongodb.pem",27017)
        db.forecast.public.sev.save(data)

    return

def clean_up(resultDir):

    move("{0}/SPRUCE_pars.txt".format(resultDir),"{0}/input/SPRUCE_pars.txt".format(resultDir))
    move("{0}/SPRUCE_yearly.txt".format(resultDir),"{0}/output/SPRUCE_yearly.txt".format(resultDir))
    for mvfile in glob("{0}/Simu_dailyflux*.txt".format(resultDir)):
        move(mvfile, "{0}/output".format(resultDir))
    for mvfile in glob("{0}/*.png".format(resultDir)):
        move(mvfile, "{0}/plot".format(resultDir))

    # Yuanyuan add to clear up forecast_csv
    #current_date=datetime.now().strftime("%Y-%m-%d")
    current_date=datetime.now().strftime("%Y")
    #if not os.path.exists("{0}/forecast_csv/{1}".format(basedir,current_date)):
    #    os.makedirs("{0}/forecast_csv/{1}".format(basedir,current_date))
    
    # make one folder for all the time, changed 01_04_2017
    if not os.path.exists("{0}/forecast_csv/ecopad_vdv".format(basedir)):
        os.makedirs("{0}/forecast_csv/ecopad_vdv".format(basedir))

    #for afile in glob.iglob("{0}/forecast_csv/{1}*".format(basedir,current_date)):
    #	print afile
    # 	os.remove(afile)
   
    try: 
        for mvfile in glob("{0}/*.csv".format(resultDir)):
            head,tail=os.path.split(mvfile)
            #dst_file=os.path.join("{0}/forecast_csv/{1}/{2}".format(basedir,current_date,tail))
            # modified 01_04_2017
            dst_file=os.path.join("{0}/forecast_csv/ecopad_vdv/{1}".format(basedir,tail))
            i=1 
            if os.path.exists(dst_file):
                with open(dst_file, 'a') as singleFile:
                    for line in open(mvfile, 'r'):
                       if i > 1:
                          singleFile.write(line)          
                          #print i
                       i=2
                os.remove(mvfile)
        else: 
            #move(mvfile,"{0}/forecast_csv/{1}".format(basedir,current_date))
            move(mvfile,"{0}/forecast_csv/ecopad_vdv".format(basedir)) 
    except:
        pass 

    try:
        move("{0}/SPRUCE_da_pars.txt".format(resultDir),"{0}/input/SPRUCE_da_pars.txt".format(resultDir))
        move("{0}/Paraest.txt".format(resultDir),"{0}/input/Paraest.txt".format(resultDir))
    except:
        pass

#chang added_060318
def clean_up_v2_0(resultDir):

    move("{0}/SPRUCE_v2_0_pars.txt".format(resultDir),"{0}/input/SPRUCE_v2_0_pars.txt".format(resultDir))
    move("{0}/SPRUCE_yearly.txt".format(resultDir),"{0}/output/SPRUCE_yearly.txt".format(resultDir))
    for mvfile in glob("{0}/Simu*.txt".format(resultDir)):
        move(mvfile, "{0}/output".format(resultDir))
    for mvfile in glob("{0}/*.png".format(resultDir)):
        move(mvfile, "{0}/plot".format(resultDir))

    # Yuanyuan add to clear up forecast_csv
    #current_date=datetime.now().strftime("%Y-%m-%d")
    current_date=datetime.now().strftime("%Y")
    #if not os.path.exists("{0}/forecast_csv/{1}".format(basedir,current_date)):
    #    os.makedirs("{0}/forecast_csv/{1}".format(basedir,current_date))

    # make one folder for all the time, changed 01_04_2017
    if not os.path.exists("{0}/forecast_csv/ecopad_vdv".format(basedir)):
        os.makedirs("{0}/forecast_csv/ecopad_vdv".format(basedir))

    #for afile in glob.iglob("{0}/forecast_csv/{1}*".format(basedir,current_date)):
    #   print afile
    #   os.remove(afile)

    try:
        for mvfile in glob("{0}/*.csv".format(resultDir)):
            head,tail=os.path.split(mvfile)
            #dst_file=os.path.join("{0}/forecast_csv/{1}/{2}".format(basedir,current_date,tail))
            # modified 01_04_2017
            dst_file=os.path.join("{0}/forecast_csv/ecopad_vdv/{1}".format(basedir,tail))
            i=1
            if os.path.exists(dst_file):
                with open(dst_file, 'a') as singleFile:
                    for line in open(mvfile, 'r'):
                       if i > 1:
                          singleFile.write(line)
                          #print i
                       i=2
                os.remove(mvfile)
        else:
            #move(mvfile,"{0}/forecast_csv/{1}".format(basedir,current_date))
            move(mvfile,"{0}/forecast_csv/ecopad_vdv".format(basedir))
    except:
        pass

    try:
        move("{0}/SPRUCE_v2_0_da_pars.txt".format(resultDir),"{0}/input/SPRUCE_v2_0_da_pars.txt".format(resultDir))
        move("{0}/Paraest.txt".format(resultDir),"{0}/input/Paraest.txt".format(resultDir))
    except:
        pass
##end
def clean_up_v2_2(resultDir):

    #move("{0}/SPRUCE_pars_ws.txt".format(resultDir),"{0}/input/SPRUCE_pars_ws.txt".format(resultDir))
    #move("{0}/SPRUCE_yearly.csv".format(resultDir),"{0}/output/SPRUCE_yearly.csv".format(resultDir))
    for mvfile in glob("{0}/*.txt".format(resultDir)):
        move(mvfile, "{0}/output".format(resultDir))
    for mvfile in glob("{0}/*.csv".format(resultDir)):
        move(mvfile, "{0}/output".format(resultDir))
    for mvfile in glob("{0}/*.png".format(resultDir)):
        move(mvfile, "{0}/plot".format(resultDir))

    # Yuanyuan add to clear up forecast_csv
    #current_date=datetime.now().strftime("%Y-%m-%d")
    current_date=datetime.now().strftime("%Y")
    #if not os.path.exists("{0}/forecast_csv/{1}".format(basedir,current_date)):
    #    os.makedirs("{0}/forecast_csv/{1}".format(basedir,current_date))

    # make one folder for all the time, changed 01_04_2017
    if not os.path.exists("{0}/forecast_csv/ecopad_vdv".format(basedir)):
        os.makedirs("{0}/forecast_csv/ecopad_vdv".format(basedir))

    #for afile in glob.iglob("{0}/forecast_csv/{1}*".format(basedir,current_date)):
    #   print afile
    #   os.remove(afile)

    try:
        for mvfile in glob("{0}/*.csv".format(resultDir)):
            head,tail=os.path.split(mvfile)
            #dst_file=os.path.join("{0}/forecast_csv/{1}/{2}".format(basedir,current_date,tail))
            # modified 01_04_2017
            dst_file=os.path.join("{0}/forecast_csv/ecopad_vdv/{1}".format(basedir,tail))
            i=1
            if os.path.exists(dst_file):
                with open(dst_file, 'a') as singleFile:
                    for line in open(mvfile, 'r'):
                       if i > 1:
                          singleFile.write(line)
                          #print i
                       i=2
                os.remove(mvfile)
        else:
            #move(mvfile,"{0}/forecast_csv/{1}".format(basedir,current_date))
            move(mvfile,"{0}/forecast_csv/ecopad_vdv".format(basedir))
    except:
        pass

    try:
        move("{0}/SPRUCE_da_pars_c.txt".format(resultDir),"{0}/input/SPRUCE_da_pars_c.txt".format(resultDir))
        move("{0}/Paraest.txt".format(resultDir),"{0}/input/Paraest.txt".format(resultDir))
    except:
        pass

def clean_up_SEV(resultDir):

    move("{0}/SEV_pars.txt".format(resultDir),"{0}/input/SEV_pars.txt".format(resultDir))
    for mvfile in glob("{0}/Simu*.txt".format(resultDir)):
        move(mvfile, "{0}/output".format(resultDir))
    for mvfile in glob("{0}/*.png".format(resultDir)):
        move(mvfile, "{0}/plot".format(resultDir))

    # Yuanyuan add to clear up forecast_csv
    #current_date=datetime.now().strftime("%Y-%m-%d")
    current_date=datetime.now().strftime("%Y")
    #if not os.path.exists("{0}/forecast_csv/{1}".format(basedir,current_date)):
    #    os.makedirs("{0}/forecast_csv/{1}".format(basedir,current_date))

    # make one folder for all the time, changed 01_04_2017
    if not os.path.exists("{0}/forecast_csv/ecopad_vdv".format(basedir)):
        os.makedirs("{0}/forecast_csv/ecopad_vdv".format(basedir))

    #for afile in glob.iglob("{0}/forecast_csv/{1}*".format(basedir,current_date)):
    #   print afile
    #   os.remove(afile)

    try:
        for mvfile in glob("{0}/*.csv".format(resultDir)):
            head,tail=os.path.split(mvfile)
            #dst_file=os.path.join("{0}/forecast_csv/{1}/{2}".format(basedir,current_date,tail))
            # modified 01_04_2017
            dst_file=os.path.join("{0}/forecast_csv/ecopad_vdv/{1}".format(basedir,tail))
            i=1
            if os.path.exists(dst_file):
                with open(dst_file, 'a') as singleFile:
                    for line in open(mvfile, 'r'):
                       if i > 1:
                          singleFile.write(line)
                          #print i
                       i=2
                os.remove(mvfile)
        else:
            #move(mvfile,"{0}/forecast_csv/{1}".format(basedir,current_date))
            move(mvfile,"{0}/forecast_csv/ecopad_vdv".format(basedir))
    except:
        pass

    try:
        move("{0}/SEV_da_pars.txt".format(resultDir),"{0}/input/SEV_da_pars.txt".format(resultDir))
        move("{0}/Paraest.txt".format(resultDir),"{0}/input/Paraest.txt".format(resultDir))
    except:
        pass

### Xin modify in 072519
def clean_up_elm1(resultDir):
#def clean_up_elm1(results_elm, resultDir):
    #move("{0}".format(results_elm),"{0}/output/".format(resultDir))
    if not os.path.exists("{0}/forecast_csv/ecopad_elm".format(basedir)):
        os.makedirs("{0}/forecast_csv/ecopad_elm".format(basedir))

    try:
        for mvfile in glob("{0}/results/forecasting_*.csv".format(resultDir)):
            head,tail=os.path.split(mvfile)
            dst_file=os.path.join("{0}/forecast_csv/ecopad_elm/{1}".format(basedir,tail))
            i=1
            if os.path.exists(dst_file):
                with open(dst_file, 'a') as singleFile:
                    for line in open(mvfile, 'r'):
                       if i > 1:
                          singleFile.write(line)
                          #print i
                       i=2
                os.remove(mvfile)
            else:
                move(mvfile,"{0}/forecast_csv/ecopad_elm".format(basedir))
    except:
        pass
	
def clean_up_elm2(task_id):
    move("/plots/[0]/daily".format(task_id),"/plot/")
		
def create_template(tmpl_name,params,resultDir,check_function):
    tmpl = os.path.join(os.path.dirname(__file__),'templates/{0}.tmpl'.format(tmpl_name))
    with open(tmpl,'r') as f:
        template=Template(f.read())
    params_file = os.path.join(resultDir,'{0}.txt'.format(tmpl_name))
    with open(params_file,'w') as f2:
        f2.write(template.render(check_function(params)))
    return '{0}.txt'.format(tmpl_name)

def create_report(tmpl_name,data,resultDir):
    tmpl = os.path.join(os.path.dirname(__file__),'templates/{0}.tmpl'.format(tmpl_name))
    with open(tmpl,'r') as f:
        template=Template(f.read())
    report_file = os.path.join(resultDir,'{0}.htm'.format(tmpl_name))
    with open(report_file,'w') as f2:
        f2.write(template.render(data))
    return '{0}.htm'.format(tmpl_name)

def setup_result_directory(task_id):
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    os.makedirs(resultDir)
    os.makedirs("{0}/input".format(resultDir))
    os.makedirs("{0}/output".format(resultDir))
    os.makedirs("{0}/plot".format(resultDir))
    return resultDir 
	
def setup_result_directory_ws(task_id):
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    os.makedirs(resultDir)
    os.makedirs("{0}/input".format(resultDir))
    os.makedirs("{0}/output".format(resultDir))
    os.makedirs("{0}/plot".format(resultDir))
    return resultDir 

def setup_result_directory_ws_2020(task_id):
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    os.makedirs(resultDir)
    os.makedirs("{0}/input".format(resultDir))
    os.makedirs("{0}/output_increased".format(resultDir))
    os.makedirs("{0}/output_decreased".format(resultDir))
    os.makedirs("{0}/plot".format(resultDir))
    return resultDir

def setup_result_directory_ws_2020_default(task_id):
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    os.makedirs(resultDir)
    os.makedirs("{0}/input".format(resultDir))
    os.makedirs("{0}/output/SPRUCE".format(resultDir))
    os.makedirs("{0}/output/DA_cflux".format(resultDir))
    os.makedirs("{0}/output/DA_cpool".format(resultDir))
    os.makedirs("{0}/output/DA_cpool_cflux".format(resultDir))
    os.makedirs("{0}/output/DA_nomeasure".format(resultDir))
    os.makedirs("{0}/plot/DAUnit3".format(resultDir))
    return resultDir
	
def elm_setup_result_directory(task_id):
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    os.makedirs(resultDir)
    os.makedirs("{0}/run".format(resultDir))
    os.makedirs("{0}/plot".format(resultDir))
    return resultDir 

def setup_result_directory(task_id):
    resultDir = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    os.makedirs(resultDir)
    #os.makedirs("{0}/input".format(resultDir))
    os.makedirs("{0}/output_data".format(resultDir))
    #os.makedirs("{0}/plot".format(resultDir))
    return resultDir 

def check_params(pars):
    """ Check params and make floats."""
    for param in ["latitude","longitude","wsmax","wsmin","LAIMAX","LAIMIN","SapS","SLA","GLmax","GRmax","Gsmax",
                    "extkU","alpha","Tau_Leaf","Tau_Wood","Tau_Root","Tau_F","Tau_C","Tau_Micro","Tau_SlowSOM",
                    "gddonset","Rl0" ]:
        try:
            inside_check(pars,param)
        except:
            pass
        try:
            inside_check(pars, "min_{0}".format(param))
        except:
            pass
        try:
            inside_check(pars, "max_{0}".format(param))
        except:
            pass
    return pars  

def check_params_SEV2(pars):
    """ Check params and make floats."""
    for param in ["rdepth","SLA","stom_n","Ds0","Vcmax","tau_L","tau_S","tau_R","tau_F","tau_C","tau_Micr","tau_Slow",
					"tau_Pass","gddonset","Q10","gcostpro","mresp20_1","mresp20_2","mresp20_3","Q10paccrate_1","Q10paccrate_2",
					"Q10paccrate_3","Topt","Ha","Hd","f_F2M","f_C2M","f_C2S","f_M2S","f_M2P","f_S2P","f_S2M","f_P2M","basew4sresp"]:
        try:
            inside_check(pars,param)
        except:
            pass
        try:
            inside_check(pars, "min_{0}".format(param))
        except:
            pass
        try:
            inside_check(pars, "max_{0}".format(param))
        except:
            pass
    return pars	
	
def check_params_v2_0(pars):
    """ Check params and make floats."""
    for param in ["latitude","longitude","wsmax","wsmin","LAIMAX","LAIMIN","SapS","SLA","GLmax","GRmax","Gsmax",
                    "extkU","alpha","Tau_Leaf","Tau_Wood","Tau_Root","Tau_F","Tau_C","Tau_Micro","Tau_SlowSOM",
                    "gddonset","Rl0","r_me","Q10pro","kCH4","Omax","CH4_thre","Tveg","Tpro_me","Toxi" ]:
        try:
            inside_check(pars,param)
        except:
            pass
        try:
            inside_check(pars, "min_{0}".format(param))
        except:
            pass
        try:
            inside_check(pars, "max_{0}".format(param))
        except:
            pass
    return 

def check_params_ws(pars):
    """ Check params and make floats."""
    for param in ["latitude","longitude","wsmax","wsmin","LAIMAX","LAIMIN","SapS","SLA","GLmax","GRmax","Gsmax",
                    "extkU","alpha","Tau_Leaf","Tau_Wood","Tau_Root","Tau_F","Tau_C","Tau_Micro","Tau_SlowSOM",
                    "gddonset","Rl0","r_me","Q10pro","kCH4","Omax","CH4_thre","Tveg","Tpro_me","Toxi","f","bubprob",
					"Vmaxfraction","Q10rh","JV","Entrpy"]:
        try:
            inside_check(pars,param)
        except:
            pass
        try:
            inside_check(pars, "min_{0}".format(param))
        except:
            pass
        try:
            inside_check(pars, "max_{0}".format(param))
        except:
            pass
    return pars	

def check_params_ws_2020(pars):
    """ Check params and make floats."""
    for param in ["latitude","longitude","wsmax","wsmin","LAIMAX","LAIMIN","rdepth","Rootmax","Stemmax","SapR",
                    "SapS","SLA","GLmax","GRmax","Gsmax","stom_n","a1","Ds0","Vcmx0","extkU","xfang","alpha",
                    "Tau_Leaf","Tau_Wood","Tau_Root","Tau_F","Tau_C","Tau_Micro","Tau_SlowSOM","Tau_Passive",
                    "gddonset","Q10","Rl0","Rs0","Rr0","r_me","Q10pro","kCH4","Omax","CH4_thre","Tveg","Tpro_me",
                    "Toxi","f","bubprob","Vmaxfraction","Q10rh","JV","Entrpy","shcap_snow","condu_snow","condu_b",
                    "albedo_snow","fa","fsub","rho_snow","decay_m","depth_ex"]:
        try:
            inside_check(pars,param)
        except:
            pass
        try:
            inside_check(pars, "min_{0}".format(param))
        except:
            pass
        try:
            inside_check(pars, "max_{0}".format(param))
        except:
            pass
    return pars	

def inside_check(pars,param):
    if not "." in str(pars[param]):
        pars[param]="%s." % (str(pars[param]))
    else:
        pars[param]=str(pars[param])  

def zip_folder(task_id):
    dirname = os.path.join(basedir, 'ecopad_tasks2/', task_id)
    zipfilename = dirname + "/" + task_id + ".zip"
    filelist = []
    if os.path.isfile(dirname):
        filelist.append(dirname)
    else :
        for root, dirs, files in os.walk(dirname,topdown=False):
            if not files and not dirs:
                filelist.append(root)
            for name in files:
                filelist.append(os.path.join(root, name))
    zf = zipfile.ZipFile(zipfilename, "w", zipfile.zlib.DEFLATED)
    for tar in filelist:
        arcname = tar[len(dirname):]
        zf.write(tar,arcname)
    zf.close()

def rename_par_file(task_id):
    dirname = os.path.join(basedir, "ecopad_tasks2", task_id, "input")
    oldname = dirname + "/" + "SPRUCE_workshop_2020.txt"
    newname = dirname + "/" + "SPRUCE_pars.txt"
    os.rename(oldname, newname)

def rename_da_file(task_id):
    dirname = os.path.join(basedir, "ecopad_tasks2", task_id, "input")
    oldname = dirname + "/" + "SPRUCE_workshop_2020_da.txt"
    newname = dirname + "/" + "SPRUCE_da_pars.txt"
    os.rename(oldname, newname)

def copy_task_result(source_path, target_path):
    for root, dirs, files in os.walk(source_path):
        for file in files:
            src_file = os.path.join(root, file)
            shutil.copy(src_file, target_path)

