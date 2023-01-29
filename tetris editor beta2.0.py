from tkinter import *
from tkinter.messagebox import *
from py_fumen.encoder import encode
from py_fumen.field import Field, create_inner_field
from py_fumen.page import Page

DEBUG = False
#------------------------------------------#
# 0.initialization data storage        
#------------------------------------------#

# store piece painting information
class Config:
    auto_mode = True
    paint_piece = 'G'
    paint_positions = []
    last_paint_pos = (-1,-1)

# store setup information in a tree structure
class Setup:
    all = []
    root = None
    stack = []
    def __init__(self, name, fullid, board = None):
        self.name = name
        self.fullid = fullid
        
        if board is None:
            self.board = [['N' for i in range(10)] for j in range(20)]
        else:
            self.board = board 
        self.members = dict()

        if fullid != '':
            Setup.all.append(self)

    def search(self, subid):
        if subid == '':
            return self

        parentsubid, sym, childid = subid.partition('.')
        if parentsubid not in self.members:
            showerror(title = 'search error', message = f' invalid setup id [{parentsubid}]! the savefile may be corrupted!')
            return None
        if childid != '':
            return self.members[parentsubid].search(childid)
        else:
            return self.members[parentsubid]

    def create(self, name, board):
        #create the newsetup with specified name or board into the setup, id will be aumotically generated
        max_id = 0
        for i in self.members:
            max_id = max(int(i) , max_id)
        subid = str(max_id+1)
        newsetup = Setup(name = name, fullid = (self.fullid + '.' + subid).strip('.'), board = board)
        self.members[subid] = newsetup
        return newsetup

    def insert(self, newsetup):
        #insert the newsetup  into the setup
        parentid, sym, childsubid = newsetup.fullid.rpartition('.')
        parent = Setup.root.search(parentid)

        if parent is None:
            showerror(title = 'insert error', message = f' invalid setup id [{parentid}]! the savefile may be corrupted!')
        for used_setup in parent.members.values():
            if used_setup.name == newsetup.name:
                showerror(title = 'duplicate error', message = f'setup with same name [{newsetup.name}] is not allowed! the savefile may be corrupted!')

        parent.members[childsubid] = newsetup
    
    def delete(self, parent = None):
        if parent is None:
            parentid, sym, childsubid = self.fullid.rpartition('.')
            parent = Setup.root.search(parentid)
            parent.members.pop(childsubid)
        for setup in self.members.values():
            setup.delete(parent = self)
        Setup.all.remove(self)

    def masterload():
        try:
            with open('multisave.txt','r') as file:
                data = file.read().strip().splitlines()
                for row in data:
                    if row.startswith('setup:'):
                        if DEBUG: print('reading', row)
                        name = row.partition('setup:')[2]

                    elif row.startswith('id:'):
                        if DEBUG: print('with', row)
                        fullid = row.partition('id:')[2]
                        setupboard = []

                    elif row.startswith('----------'):
                        while len(setupboard) <20:
                            setupboard.append(list('NNNNNNNNNN'))
                        newsetup = Setup(name, fullid, setupboard)
                        Setup.root.insert(newsetup)

                    else:
                        setupboard.insert(0, row)
        except IOError:
            with open('multisave.txt','w') as file:
                pass

    def mastersave():
        with open('multisave.txt','w') as file:
            for setup in (Setup.all):
               
                file.write(f'setup:{setup.name}\n')
                file.write(f'id:{setup.fullid}\n')
                for row in setup.board[::-1]:
                    file.write(''.join(row)+'\n')
                file.write('----------\n')

    def __str__(self):
        return self.name

Setup.root = Setup(name = 'start', fullid = '')
Setup.masterload()
Setup.stack.append(Setup.root)
# the board of tetris
board = [['N' for i in range(10)] for j in range(20)]
board_rects = []
preview1_rects = []
preview2_rects = []
# for mapping piece to color
color_table = {'Z': 'red',
               'L': 'orange',
               'O': 'yellow',
               'S': 'lime',
               'I': 'cyan',
               'J': 'blue',
               'T': 'magenta',
               'G': 'silver',
               'N': 'black',
               }

# for mapping piece to their shapes
shape_table = {'Z': [{(1, 0), (0, 2), (1, 1), (0, 1)},  {(1, 0), (1, 1), (2, 1), (0, 0)}],
               'L': [{(1, 0), (0, 1), (2, 0), (0, 0)}, {(0, 1), (0, 2), (1, 2), (0, 0)}, {(0, 1), (1, 1), (2, 0), (2, 1)}, {(1, 0), (1, 1), (1, 2), (0, 0)}],
               'O': [{(1, 0), (0, 1), (1, 1), (0, 0)}],
               'S': [{(0, 1), (1, 1), (1, 2), (0, 0)}, {(1, 0), (1, 1), (2, 0), (0, 1)}],
               'I': [{(1, 0), (2, 0), (0, 0), (3, 0)},  {(0, 1), (0, 2), (0, 3), (0, 0)}],
               'J': [{(0, 1), (1, 1), (2, 1), (0, 0)}, {(0, 1), (1, 0), (0, 2), (0, 0)}, {(1, 0), (2, 0), (2, 1), (0, 0)}, {(1, 0), (1, 1), (1, 2), (0, 2)}],
               'T': [{(0, 1), (0, 2), (1, 1), (0, 0)}, {(1, 0), (1, 1), (2, 0), (0, 0)}, {(1, 0), (1, 1), (1, 2), (0, 1)}, {(1, 0), (1, 1), (2, 1), (0, 1)}],
               }


#------------------------------------------#
# 1.initialize root window                   
#------------------------------------------#
root = Tk()
root.geometry('1200x680+0+0')


#---------------------------------------------#
# 2.initialize frame, gamebox to display board                 
#---------------------------------------------#
namelabel = Label(width = 10, font=('Arial', 10), text = 'setup name')
namelabel.place(x=50,y=10)
namebox = Entry(width = 60, font=('Arial', 10))
namebox.place(x=50,y=30)

tetrisframe = Frame(root, bg='black', padx=2, pady=2, height = 680, width = 600)
tetrisframe.place(x=50, y=50)

gameBox = Canvas(tetrisframe, width=298, height=598, bg='black', relief = FLAT)
gameBox.pack(side = 'left')

navigatorframe = Frame(root, bg='white', padx=2, pady=2, height = 680, width = 600)
navigatorframe.place(x=700, y=50)

previewframe = Frame(root, padx=2, pady=2, height = 300, width = 400)
previewframe.place(x=700, y=300)

label1 = Label(text = 'start',font=('Arial', 10), height = 3, width = 20)
label1.place(x=700, y=250)

label2 = Label(text = 'start',font=('Arial', 10), height = 3, width = 20)
label2.place(x=925, y=250)

previewbox1 = Canvas(previewframe, width=150, height=300, bg='grey')
previewbox1.pack(side = 'left')

rightarrow = Label(previewframe, text = '→',font=('Arial', 20), width=4, height=4)
rightarrow.pack(side = 'left')

previewbox2 = Canvas(previewframe, width=150, height=300, bg='grey')
previewbox2.pack(side = 'left')

#navigator = Canvas(navigatorframe, width=400, height=600, bg='white', relief = FLAT)
#navigator.pack(side = 'left')
def init_rectangles():
    if DEBUG: print('initialize squares of tetris board')

    #draw gridline
    for i in range(1,10):
        gameBox.create_line(30*i, 0, 30*i, 602, width=1, fill='white')
        previewbox1.create_line(15*i, 0, 15*i, 300, width=1, fill='white')
        previewbox2.create_line(15*i, 0, 15*i, 300, width=1, fill='white')
    for j in range(1,20):
        gameBox.create_line(0, 30*j, 602, 30*j, width=1, fill='white')
        previewbox1.create_line(0, 15*j, 300, 15*j, width=1, fill='white')
        previewbox2.create_line(0, 15*j, 300, 15*j, width=1, fill='white')
        
    #draw board
    for j in range(20):
        board_rects.append([])
        preview1_rects.append([])
        preview2_rects.append([])
        for i in range(10):
            color = color_table[board[j][i]]
            rect = gameBox.create_rectangle(30*i, -30*(j-20), 30*(i+1), -30*(j-19), width=1, fill=color, outline = 'white')               
            board_rects[-1].append(rect)

            preivewrect1 = previewbox1.create_rectangle(15*i, -15*(j-20), 15*(i+1), -15*(j-19), width=1, fill=color, outline = 'white')               
            preview1_rects[-1].append(preivewrect1)

            preivewrect2 = previewbox2.create_rectangle(15*i, -15*(j-20), 15*(i+1), -15*(j-19), width=1, fill=color, outline = 'white')               
            preview2_rects[-1].append(preivewrect2)
init_rectangles()


#----------------------------------------------------#
# 3.initialize line clear button and related function           
#----------------------------------------------------#
def line_clear(event):
    line = 19- (event.widget.winfo_y()-55)//30
    if DEBUG: print('clearing line',line)
    for j in range(line,19):
        for i in range(10):
            board[j][i] = board[j+1][i]
    for i in range(10):
        board[19][i] = 'N'
    render()
    
line_clear_buttons = []

def set_line_clear_button():
    for j in range(20):
        line_clear_button = Button(root, text="clear", width=4, height=1, font=('Arial', 10))
        line_clear_buttons.append(line_clear_button)
        line_clear_button.bind('<ButtonRelease-1>', line_clear)
        #line_clear_button.place(x=0, y=55+j*30)

set_line_clear_button()


#--------------------------------------------------------------------------#
# 4.1 render function to change color of canva and update line clear button
#--------------------------------------------------------------------------#
def update_line_clear_button():
    for j in range(20):
        if board[j].count('N') == 0:
            if DEBUG: print('you can now clear line', j)
            line_clear_buttons[j].place(x=0, y=55+(19-j)*30)
        else:
            line_clear_buttons[j].place_forget()

def render(specific_position = None):
    if specific_position is not None:
        if DEBUG: print('rendering positions: ', specific_position)
        j, i = specific_position
        color = color_table[board[j][i]]
        gameBox.itemconfig(board_rects[j][i], fill = color)
    else:
        if DEBUG: print('rendering all positions') 
        for j in range(20):
            for i in range(10):
                color = color_table[board[j][i]]
                gameBox.itemconfig(board_rects[j][i], fill = color)
    update_line_clear_button()

#--------------------------------------------------------------------------#
# 4.2 render preview function to change color of preivew
#--------------------------------------------------------------------------#
def render_preview():
    if DEBUG: print('rendering preview1')
    previous_board = Setup.stack[-2:][0].board
    label1.config(text = Setup.stack[-2:][0].name)
    for j in range(20):
        for i in range(10):
            color = color_table[previous_board[j][i]]
            previewbox1.itemconfig(board_rects[j][i], fill = color)
    if DEBUG: print('rendering preview2')
    next_board = Setup.stack[-1].board
    label2.config(text = Setup.stack[-1].name)
    for j in range(20):
        for i in range(10):
            color = color_table[next_board[j][i]]
            previewbox2.itemconfig(board_rects[j][i], fill = color)

#---------------------------------------------------#
# 5.clear board button and function 
#---------------------------------------------------#          
def clear_board():
    if DEBUG: print('clear board')
    for j in range(20):
        for i in range(10):
            board[j][i] = 'N'
    render()

clear_board_button = Button(root, text="Clear Board", width=10, height=1, font=('Arial', 20), command = clear_board)
clear_board_button.place(x=500, y=50)


#---------------------------------------------------#
# 6.color button to choose paint color
#---------------------------------------------------#
Pixel = PhotoImage(width=1, height=1)
color_buttons = [Button(root, text=piece, width=40, height=40, font=('Arial', 20), background = color_table[piece], image=Pixel, compound="c") for piece in 'ZLOSIJTG']

def choose_color(event):
    new_piece = event.widget.cget('text')
    color_buttons['ZLOSIJTG'.index(Config.paint_piece)].configure(relief = 'raised')
    auto_button.configure(relief = 'raised')
    Config.paint_piece = new_piece
    Config.auto_mode = False
    event.widget.configure(relief = 'groove')
    
for button, piece,idx in zip(color_buttons, 'ZLOSIJTG',range(8)):
    button.place(x=400, y=200+60*idx)
    button.bind('<ButtonRelease-1>', choose_color)


#-------------------------------------------------------------------------------#
# 7.auto button to automatically paint color by detecting tetramino
#-------------------------------------------------------------------------------#
def choose_auto_mode(event):
    color_buttons['ZLOSIJTG'.index(Config.paint_piece)].configure(relief = 'raised')
    Config.paint_piece = 'G'
    Config.auto_mode = True
    event.widget.configure(relief = 'groove')

auto_button = Button(root, text='AUTO', width=40, height=40, font=('Arial', 10), background = 'white',relief = 'groove', image=Pixel, compound="c")
auto_button.place(x=400, y=140)
auto_button.bind('<ButtonRelease-1>', choose_auto_mode)


#---------------------------------------------------#
# 8.save and saveas button
#---------------------------------------------------#
def save(): #save
    if DEBUG: print('save')
    setup_name = namebox.get()
    if setup_name == '':
        showerror(title = 'save error', message = f' setup name cannot be none!')
        if DEBUG: print('setup name cannot be none')
        return

    if len(Setup.stack)>1:
        new_setup_path = '\\'.join(setup.name for setup in Setup.stack)
        if not askyesno(title = 'save', message = f'are you sure you want to replace setup {new_setup_path}?'):
            return
        parent = Setup.stack[-2]
        #avoid duplicate setup name
        for used_setup in parent.members.values():
            if used_setup.name == setup_name and used_setup.fullid != Setup.stack[-1].fullid:
                showerror(title = 'setup name used', message = f'setup name used, you cannot rename setup to {setup_name}!')
                if DEBUG: print('setup name used')
                return
        Setup.stack[-1].name = setup_name
        Setup.stack[-1].board = [[cell for cell in row] for row in board]
        Setup.mastersave()
        cd.delete(0,'end')
        cd.insert(0, '\\'.join(setup.name for setup in Setup.stack))
        render_preview()
    else:
        saveas()

def saveas(): #save
    setup_name = namebox.get()
    if setup_name == '':
        showerror(title = 'save error', message = f' setup name cannot be none!')
        if DEBUG: print('setup name cannot be none')
        return
    #avoid duplicate setup name
    parent = Setup.stack[-1]
    for used_setup in parent.members.values():
        if used_setup.name == setup_name:
            isreplace = askyesno(title = 'setup name used', message = f'setup name used, do you want to replace setup {setup_name}?')
            if isreplace:
                used_setup.board = [[cell for cell in row] for row in board]
                Setup.mastersave()
                load_setup(setup_name)
            return
    new_setup_path = '\\'.join(setup.name for setup in Setup.stack) + '\\' + setup_name
    if not askyesno(title = 'setup name used', message = f'are you sure you want to save this setup as {new_setup_path}?'):
        return
    Setup.stack[-1].create(name = namebox.get(), board = [[cell for cell in row] for row in board])
    Setup.mastersave()

    load_setup(setup_name)

save_button = Button(root, text="Save", width=10, height=1, font=('Arial', 20), command = save)
save_button.place(x=500, y=250)

saveas_button = Button(root, text="Save As", width=10, height=1, font=('Arial', 20), command = saveas)
saveas_button.place(x=500, y=350)


#---------------------------------------------------#
# 9.reload button
#---------------------------------------------------#
def reload():
    if DEBUG: print('reload board')
    for idx, row in enumerate(Setup.stack[-1].board):
        board[idx] = list(row)
    render()

reload_button = Button(root, text="Reload Board", width=10, height=1, font=('Arial', 20), command = reload)
reload_button.place(x=500, y=150)


#------------------------------------------------------------#
# 10. initalize toolbar (setup path textbox and goback button)
#------------------------------------------------------------#
directoryframe = Frame(navigatorframe, bg='white', padx=2, pady=2, height = 40, width = 800)
directoryframe.pack()

goback = Button(directoryframe, text="↑", width=2, height=1, font=('Arial', 10))
goback.pack(side = 'left')

cd = Entry(directoryframe, width = 60, font=('Arial', 10))
cd.pack(side = 'left',expand = 'yes', fill = 'both')
cd.insert(0, 'start')




'''goto = Button(directoryframe, text="→", width=2, height=1, font=('Arial', 10))
goto.pack(side = 'left')'''


#----------------------------------------------------------------------#
# 11. initalize navigator (setup listbox) to show next possible setup
#----------------------------------------------------------------------#
setup_listbox = Listbox(navigatorframe)
setup_listbox.pack(side = 'bottom', expand = 'yes', fill = 'both')

#---------------------------------------------------------#
# 12. load board when clicking setup name shown in listbox
#---------------------------------------------------------#
def fetch_cd():
    namebox.delete(0, 'end')
    namebox.insert(0,Setup.stack[-1].name)

    cd.delete(0,'end')
    cd.insert(0, '\\'.join(setup.name for setup in Setup.stack))
    cd.xview('end')
    
    setup_listbox.delete(0, 'end')
    setups = list(Setup.stack[-1].members.items())
    setups.sort(key = lambda x: int(x[0]))
    for key, setup in setups:
        setup_listbox.insert('end', setup.name)  

def load_setup(setup_name):
    if DEBUG: print('loading setup: ', setup_name)
    #update cd
    if setup_name == '':
        return
    #cd.insert(len(cd.get()), f'\{setup_name}')
    #update setup
    for setupi in Setup.stack[-1].members.values():
        if setupi.name == setup_name:
            setup = setupi
            break
    else:
        if DEBUG: print(f'{setup_name }not found')
    Setup.stack.append(setup)
    #update listbox
    fetch_cd()
    #load board
    for idx, row in enumerate(setup.board):
        board[idx] = list(row) 
    render()
    render_preview()

fetch_cd()
setup_listbox.bind('<<ListboxSelect>>', lambda event: load_setup(setup_listbox.get(ANCHOR)))


#---------------------------------------------------------#
# 13. delete button
#---------------------------------------------------------#
def delete():
    if len(Setup.stack) > 1:
        path = '\\'.join(setup.name for setup in Setup.stack)
        if not askyesno(title = 'delete', message = f'are you sure you want to delete setup {path} and its following setup?'):
            return
        setup = Setup.stack[-1]
        load_parent_setup(None)
        setup.delete()
        fetch_cd()
        Setup.mastersave()
    else:
        showerror(title = 'cannot delete start setup', message = 'cannot delete start setup')
        if DEBUG: print('cannot delete start setup')

del_button = Button(root, text="Delete", width=10, height=1, font=('Arial', 20), command = delete)
del_button.place(x=500, y=450)


#------------------------------------------------------#
# 14 go to last setup when clicking up arrow
#------------------------------------------------------#
def load_parent_setup(event):

    if len(Setup.stack) > 1:
        Setup.stack.pop()
        #update cd
        #cd.delete(0, 'end')
        #cd.insert(0, '\\'.join(setup.name for setup in Setup.stack))
        #update setup
        setup = Setup.stack[-1]
        #update listbox
        fetch_cd()
        #load board
        for idx, row in enumerate(setup.board):
            board[idx] = list(row)

        render()
        render_preview()

goback.bind('<ButtonRelease-1>', load_parent_setup)


#---------------------------------------------------#
# 15.function to paint or erase color from board
#---------------------------------------------------#

def paint(event):
    i, j = event.x//30, 19-event.y//30
    if j< 0 or j>=20 or i<0 or i>=10:
        return
    if (j,i) != Config.last_paint_pos:
        Config.last_paint_pos = (j,i)
        if DEBUG: print('painting board position',j,i)
        board[j][i] = Config.paint_piece
        Config.paint_positions.append((j,i))

        render((j,i))

def erase(event):
    i, j = event.x//30, 19-event.y//30
    if j< 0 or j>=20 or i<0 or i>=10:
        return
    if DEBUG: print('erasing board position',j,i)
    board[j][i] = 'N'
    render((j,i))


#-------------------------------------------------------#
# 16.function to relate cursor movement to paint or erase
#-------------------------------------------------------#
def activate_paint(event):
    paint(event)
    gameBox.bind('<Motion>', paint)

def deactivate_paint(event):
    gameBox.unbind('<Motion>')

def autopaint(unique_paint_positions):
    min_i=99
    min_j=99
    
    for j, i in unique_paint_positions:
        if j < min_j:
            min_j = j
        if i < min_i:
            min_i = i

    offseted_unique_paint_positions = {(j-min_j, i-min_i) for j, i in unique_paint_positions}
    
    for piece in shape_table:
        if offseted_unique_paint_positions in shape_table[piece]:
            break
    if DEBUG: print('the system has detected the piece is', piece)
    for j, i in unique_paint_positions:
        board[j][i] = piece
        render((j,i))

def paint_release(event):
    deactivate_paint(event)
    unique_paint_positions = set(Config.paint_positions)
    if Config.auto_mode == True and len(unique_paint_positions) == 4:
        autopaint(unique_paint_positions)
        if DEBUG: print('autopainted poisitons', unique_paint_positions)
    Config.paint_positions = []
    Config.last_paint_pos = (-1,-1)

def activate_erase(event):
    erase(event)
    gameBox.bind('<Motion>', erase)

def deactivate_erase(event):
    gameBox.unbind('<Motion>')


#-------------------------------------------------------#
# 17.leftclick activate paint, rightclick activate erase
#-------------------------------------------------------#
gameBox.bind('<ButtonPress-1>', activate_paint)
gameBox.bind('<ButtonRelease-1>', paint_release)
gameBox.bind('<ButtonPress-3>', activate_erase)
gameBox.bind('<ButtonRelease-3>',deactivate_erase)

#-------------------------------------------------------#
# 18.generate fumen link
#-------------------------------------------------------#
def genlink():
    pages = []

    for setup in Setup.stack:
        
        pages.append(
        Page(field=create_inner_field(Field.create(
            ''.join(''.join(i).replace('N','_') for i in reversed(setup.board)),
            '__________',
        )),
        comment=setup.name))

    fumenlink.delete(0, 'end')
    fumenlink.insert(0,'https://harddrop.com/fumen/?'+encode(pages))

fumenlink = Entry(width = 60, font=('Arial', 10))
fumenlink.place(x=700, y=650)



genlink_button = Button(text="generate fumen link", width=16, height=1, font=('Arial', 10), command = genlink)
genlink_button.place(x=500, y=650)

root.mainloop()

