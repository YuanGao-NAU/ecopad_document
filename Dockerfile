From ubuntu:18.04
RUN apt-get update
RUN apt-get install -y gfortran
COPY test.f90 /root/
WORKDIR /root
RUN gfortran -o test.o test.f90