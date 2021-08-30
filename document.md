This document aims to guide you how to create a new task in EcoPAD and publish it on the website. We will start with how to build a docker image, and then how to connect the docker image with the EcoPAD platform.

## Sample Fortran code

The following is a very simple Fortran code with the input from command line. In this example, you will learn how the code receive the arguments from command line. Copy the code to an empty file (**e.g., test.f90**). 

```Fortran
program main

    character(len=10) first_command_line_argument   !declaration
    character(len=10) second_command_line_argument  !declaration

    call getarg(1, first_command_line_argument)     !get argument
    call getarg(2, second_command_line_argument)    !get argument

    print *, first_command_line_argument            !print 
    print *, second_command_line_argument           !print

end program
```

Compile the file with the following command:

```Bash
gfortran -o test.o test.f90
```

Run the executable file with the following command:

```Bash
./test.o test1 test2
```

The output should be:

```
 test1     
 test2 
```

Fortran utilizes the function ``getarg()`` to receive the arguments from command line. In the model, the paths to some crucial files are usually passed by command line arguments. Thus, it is important for us tu know how it works.

## Build a docker image

In the section, you will learn how to build a docker image together with the sample code showing above. To get started, make sure you have docker installed on your computer. Create a new file named ``Dockerfile`` in the same folder as test.f90.

### Dockerfile

```Dockerfile
From ubuntu:18.04
RUN apt-get update
RUN apt-get install -y gfortran
COPY test.f90 /root/
WORKDIR /root
RUN gfortran -o test.o test.f90
```

Run the following command to create a new docker image:

```Bash
docker build -t test:latest .
```

Once finished, you may run the docker image with:

```Bash
docker run test ./test.o test1 test2
```

In the command, ``test`` is the docker image we justed created. ``./test.o`` is the executable file in the ``WORKDIR`` of the docker image.
``test1`` and ``test2`` are two command line arguments.

## Create a new task in EcoPAD

This section will guide you how to create a new task in EcoPAD, which is very essential to further develop the platform.

Every function create in the file tasks.py with the decorator ``@task()`` can be recognized as a task in EcoPAD. You may create a new function as follows:

```Python
@task()
def test(args): 

```



