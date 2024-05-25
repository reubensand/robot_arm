import PySimpleGUI as sg
import re
import serial
import time
import process_img

'''
Reuben De Souza
Junior Design II
Block 1 Demo

Description: This programs creates a GUI and serial connection with an 
             Arduino and sends user inputted G code commands. The list of 
             accepted commands are in a constant title 'HELP'. 

             The GUI has a box to enter the commands manually, as well 
             as a pop up window with 'HELP'. The commands will be checked
             to see if they match the right format/make sense. Only if they
             pass will they be sent over serial.

             The GUI also has the option to 'Select a file'. This gets the
             filepath of an image that the user wishes to draw with the robot.
             The actual code that deciphers the image will be done later,
             so for now the path is just printed.

             The arduino code currently just repeats the message
             sent because this is a preliminary test. The actual baud
             rate will be determined later.

External Libraries: https://pyserial.readthedocs.io/en/latest/
                    https://pysimplegui.com/
'''


# Establishes connection to arduino using PySerial Library with baud rate of 9600
arduino = serial.Serial(port='COM3', baudrate=9600,timeout=1)

# Wait for the connection to establish
time.sleep(2)

FLAG = 'IMG'
E_FLAG = 'END'

# Constant that contains the accepted G/M code commands
HELP = '''G00 {X} {Y}: Move at max speed to (x, y) 
    \nG01 {X} {Y} {F}: move at feedrate to (x, y)
    \nG90: absolute mode (moves from 0)
    \nG91: relative mode (moves from last position)
    \nG20: inches
    \nG21: millimeters
    \nM02: End of program (shutdown)
    \nM06: Tool change
    \nM72: Restore modal state'''

# Font for bold parts 
TITLE = ('Comic Sans', 12, 'bold')

'''     Helper Functions       '''
def check_arguments(command: str) -> str:
    '''
    Name: check_arguments
    Argument: command (string)
    Output: 'Pass' or 'Fail'
    Description: takes the user entered g code command,
                using regular expressions it checks whether
                the command is valid. If so, the message
                is encoded and sends it to the arduino and returns 'Pass'. 
                If not, it displays a message to reference the 'help' button
                and returns 'Fail'
    '''
    # regular expression
    g_pattern = r'^G(90|91|20|21)$'
    m_pattern = r'^M(02|06|72)$'
    specific_feed = r'G01 \d+ \d+ \d+$'
    max_feed = r'G00 \d+ \d+$'

    # Test if each regex matchs
    if re.match(g_pattern, command):
        print(f'Sending g code command {command}')
        arduino.write((command + '\n').encode())
    elif re.match(m_pattern, command):
        print(f'Sending m code command {command}')
        arduino.write((command + '\n').encode())
    elif re.match(specific_feed, command):
        pieces = command.split()
        print(f'Sending G01 command {command}')
        for piece in pieces:
            print(piece)
            arduino.write((piece + '\n').encode())

    elif re.match(max_feed, command):
        pieces = command.split()
        print(f'Sending G00 command {command}')
        for piece in pieces:
            print(piece)
            arduino.write((piece + '\n').encode())
    else:
        # if none match tell user that command is invalid and return 'Fail'
        sg.popup(f'''{command} doesn\'t match the accepted patterns.\nPlease click help to see the list of commands.''')
        return 'Fail'
    # return 'Pass' if 'else' statement isn't reached
    return 'Pass'

# 
def help_window() -> None:
    '''
    Name: help_window
    Arguments: None
    Output: None
    Description: Creates a window that contains the HELP commands.
                 Uses a window to allow user to type while viewing.
                 Must close before clicking 'Send'.
    '''
    # Layout for the window
    layout = [
        # Text for help
        [sg.Text(HELP)],
        # Making sure user closes help window before sending
        [sg.Text('CLOSE BEFORE CLICKING SEND', font=TITLE)],
        [sg.Button('OK')]
    ]

    # Open the window
    window = sg.Window('Command Help', layout)

    # Loop to keep window running till closed
    while True:
        event, values = window.read()

        if event == sg.WINDOW_CLOSED or event == 'OK':
            break
    
    # Close Window
    window.close()

'''     Main Window Creation    '''
def main():
    # Sets theme of window
    sg.theme('Reddit') 

    # Defines what is displayed in the window
    layout = [
        # Creates the OSU logo
        [sg.Image(filename='logo.png', size=(300, 213))],
        # Frame that is responsible for entering the G code commands
        [sg.Frame(title='Manual G Code', layout=[
            [sg.Text("Enter G Code:")],
            [sg.InputText(key='-GCODE-', size=(50, 1))],
            [sg.Button('Send')]
        ], font=TITLE)],
        # Button to browse files and get help
        [sg.Button('Select a File'), sg.Button('Help')]
    ]

    # Create main window using layout above
    window = sg.Window('G Code Input', layout)

    # Loop of events while window is running
    while True:
        # read events from window
        event, values = window.read()

        # If 'X' or M02 events are entered, send update to Arduino, and break loop
        if event == sg.WINDOW_CLOSED or values['-GCODE-'] == 'M02':
            print("Quitting")
            arduino.write('M02'.encode())
            time.sleep(1)
            break

        # If the send button is pressed
        if event == 'Send': 
            # Read values entered in the box
            gcode = values['-GCODE-']
            # Clear the box
            window['-GCODE-'].update('')
            # send entered command to check_arguments function and save output to a variable
            check = check_arguments(gcode)
            # Wait while command is sent
            time.sleep(1)
            # If command passed tests
            if check == 'Pass':
                # Read and print message from Arduino
                while(arduino.in_waiting > 0):
                    msg = arduino.readline().decode().strip()
                    print(f'{msg}')

        # If help button is clicked call function to open help window
        elif event == 'Help':
            help_window()
        
        # If the user wants to read a file
        elif event == 'Select a File':
            # Create a popup window that only accepts file types (.png, .jpg, .jpeg) then saves filepath
            filepath = sg.popup_get_file('Select an image file', file_types=(('Image Files', '*.png'), ('Image Files', '*.jpg'), ('Image Files', '*.jpeg')))
            print(filepath)
            complexity = sg.popup('Choose the complexity of the image:', 
                          custom_text=('Simple', 'Complex'), 
                          button_type=sg.POPUP_BUTTONS_YES_NO)

            # Determine which button was pressed
            if complexity == 'Yes':
                complexity = 'Simple'
            elif complexity == 'No':
                complexity = 'Complex'
                   
            arduino.write(FLAG.encode())
            # send coordinates in here
            process_img.Process_img(filepath, complexity, arduino)
            arduino.write(E_FLAG.encode())



    # If loop is broken close arduino serial connection and GUI window 
    print('Closing serial')
    arduino.close()
    window.close()  

# Run main function
if __name__ == "__main__":
    main()
