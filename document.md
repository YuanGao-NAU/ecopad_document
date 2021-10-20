This document aims to guide you how to create a new task in EcoPAD and publish it on the website.
Every task requires it's own docker image to run. 
We will therefore first build a docker image, and then connect it to the EcoPAD platform.

## Build a docker image

In the section, you will learn how to build a docker image. To get started, make sure you have docker installed on your computer. 
Create a new directory that will contain the necessary files:

```Bash
mkdir test_api; 
cd test_api
```


### Dockerfile
Create a new file named ``Dockerfile``

```Dockerfile
From ubuntu:18.04
RUN apt-get update
RUN apt-get install -y gfortran
```

Run the following command to create the new docker image:

```Bash
docker build -t test:latest .
```

### Run the container(image) and connect to it interactively

```Bash
docker run -it test:latest bash
```
In the container type:

```Bash
gfortran -v
```
Which will give you some verbose information about the gfortran compiler and prooves that it is installed. 

## Extend the container with some Fortran code

The following is a very simple Fortran code with the input from command line. In this example, you will learn how the code receives the arguments from the command line. Copy the code to an empty file (**e.g., test.f90**) in the same directory as the `Dockerfile`.

```Fortran
program main

    character(len=10) first_command_line_argument   !declaration
    character(len=10) second_command_line_argument  !declaration

    call getarg(1, first_command_line_argument)     !get argument
    call getarg(2, second_command_line_argument)    !get argument

    print *, first_command_line_argument            !print 
    print *, second_command_line_argument           !print

end program

Fortran utilizes the function ``getarg()`` to receive the arguments from command line. In the model, the paths to some crucial files are usually passed by command line arguments. Thus, it is important for us tu know how it works.
```
Open the `Dockerfile` and add the following lines 
```
COPY test.f90 /root/
WORKDIR /root
RUN gfortran -o test.o test.f90
```

Get out of the container (Ctr-D) 
Rebuild it:
```Bash
docker build -t test:latest .
```

Once finished, you may run the docker image (this time without interaction) with:

```Bash
docker run test ./test.o test1 test2
```

In the command, ``test`` is the docker image we justed created. ``./test.o`` is the executable file in the ``WORKDIR`` of the docker image.
``test1`` and ``test2`` are two command line arguments.

## Create a new task in EcoPAD

This section will guide you how to create a new task in EcoPAD, which is very essential to further develop the platform.

Every function create in the file tasks.py with the decorator ``@task()`` can be recognized as a task in EcoPAD. 
You may create a new function in the file 
```
images_saved/config/celery/env/lib/python2.7/site-packages/ecopadq/tasks/tasks.py
```
as follows:

```Python
@task() 
def test(pars):
    task_id = str(test.request.id)
    input_a = pars["test1"]
    input_b = pars["test2"]
    docker_opts = None
    docker_cmd = "./test.o {0} {1}".format(input_a, input_b)
    result = docker_task(docker_name="test", docker_opts=None, docker_command=docker_cmd, id=task_id)
    return input_a + input_b

```



