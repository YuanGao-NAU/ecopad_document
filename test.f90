program main

    character(len=10) first_command_line_argument
    character(len=10) second_command_line_argument

    call getarg(1, first_command_line_argument)
    call getarg(2, second_command_line_argument)

    print *, first_command_line_argument
    print *, second_command_line_argument

end program