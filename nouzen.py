import os
import sys
import random
from enum import Enum
import time
import copy

def debug(msg):
    print(f"DEBUG> {msg}")

def parse_source_code(file_name):
    parsed_data = read_code(file_name)
    parsed_data = import_code(parsed_data)
    parsed_data = expand_macro(parsed_data)
    parsed_data = remove_comment(parsed_data)
    return parsed_data

def read_code(file_name):
    parsed_data = []
    if(os.path.isfile(file_name)):
        with open(file_name, encoding="utf-8") as f:
            for l in (filter(lambda x:x!=[], [split_line(e.strip()) for e in f.readlines()])):
                parsed_data += l
    else:
        print(f"File Not Found: {file_name}", file=sys.stderr)
    return parsed_data

def split_line(line):
    data_line = []
    word = ""
    is_instring = False
    is_inchar = False
    for e in line:
        if(e in [" ", "\t"] and not is_inchar):
            if(is_instring):
                word += e
            else:
                data_line.append(word)
                word = ""
        elif("\"" == e):
            if(is_instring
                and len(word) != 0
                and (word[-1] == "\\")):
                word += e
            else:
                word += e
                is_instring = not is_instring
        elif(is_instring):
            word += e
        elif(e == "'"):
            is_inchar = not is_inchar
            word += e
        elif(is_inchar):
            word += e
        else:
            is_firstblank = True
            word += e
    else:
        data_line.append(word)
        data_line.append(None)
        if(is_instring or is_inchar):
            print(f"Syntax Error {line}", file=sys.stderr)
    return [x for x in data_line if x != ""]

def import_code(parsed_data):
    is_filename = False
    file_names = []
    for i, word in enumerate(parsed_data):
        if(word == "##>"):
            is_filename = True
        elif(word == None):
            is_filename = False
        elif(is_filename):
            file_names.append([i, word])
    
    for i, name in file_names:
        code = read_code(name)
        if(len(code) != 0):
            for t in reversed(code):
                parsed_data.insert(i, t)
            parsed_data.insert(i, None)
    parsed_data = [e for e in parsed_data if e != "##>"]
    return parsed_data

def expand_macro(parsed_data):
    global macro_table
    name = ""
    is_name = False
    is_macro = False
    m = []
    macro_range = []
    replace_word = []
    for i, word in enumerate(parsed_data):
        if(word == "###" and not is_name and not is_macro):
            is_name = True
            macro_range.append([i, None])
        elif(is_name and not is_macro):
            name = word
            is_name = False
            is_macro = True
        elif(not is_name and is_macro and word != None):
            m.append(word)
        elif(is_macro and (word == None)):
            is_macro = False
            macro_range[-1][1] = i + 1
            macro_table[f"#{name}"] = copy.deepcopy(m)
            m.clear()
    for x, y in reversed(macro_range):
        del(parsed_data[x:y])
    for i, word in enumerate(parsed_data):
        if(word in macro_table):
            replace_word.append([i, word])
    for i, word in reversed(replace_word):
        parsed_data.pop(i)
        for w in reversed(macro_table[word]):
            parsed_data.insert(i, w)
    return parsed_data
    

def remove_comment(inc_data):
    data = []
    is_in_line_comment = False
    is_in_area_comment = False
    for word in inc_data:
        if(word == "#"):
            is_in_line_comment = True
        elif(word == "##"):
            is_in_area_comment = not is_in_area_comment
        elif(word == None):
            is_in_line_comment = False
        if(not (is_in_area_comment or is_in_line_comment)
            and word not in [None, "##"]):
            data.append(word)
    return data

def make_jump_table(parsed_data):
    jump_table = {}
    cond_buffer = []
    jump_buffer = []
    loop_buffer = []
    for i, word in enumerate(parsed_data):
        if(word == "("):
            cond_buffer.append(i)
        elif(word == ")"):
            jump_table[cond_buffer.pop()] = i
        if(word == "["):
            jump_buffer.append(i)
        elif(word == "]"):
            jump_table[jump_buffer.pop()] = i
        if(word == "{"):
            loop_buffer.append(i)
        elif(word == "}"):
            jump_table[i] = loop_buffer.pop()
    return jump_table


def execute(parsed_data, index, execute_code):
    global execute_option
    token = parsed_data[index]
    if(execute_option[0] != 0):
        print(f"[{index}] {token}")
    if(execute_option[1] > execute_option[2]):
        print("limit over execute token")
        return len(parsed_data)
    execute_option[1] += 1
    if token in builtin_cmd_token:
        index = builtin_cmd_token[token](parsed_data, index)
    elif token in escape_cmd_token:
        index = escape_cmd_token[token](parsed_data, index)
    elif token[0] == "\"" and token[-1] == "\"":
        index = proc_string(parsed_data, index)
    elif token in [e[1] for e in name_table]:
        index = do_named_proc(parsed_data, index, token)
    else:
        push(strtoint(token))
        index += 1
    return index

def push(value):
    data_stack.append(value)

def pop():
    v = 0
    try:
        v = data_stack.pop()
    except IndexError:
        global status_code
        v = 0
        status_code = 1
    return v

def strtoint(token):
    global status_code
    v = 0
    dict_ecs_seq = {
        "\\":"\\", "\"":"\"", "\'":"\'",
        "a":"\a", "b":"\b", "f":"\f",
        "n":"\n", "r":"\r", "t":"\t",
        "v":"\v", "e":'\x1b', "0":0
    }
    if("0d" == token[:2]):
        v = int(token[2:], 10)
    elif("0x" == token[:2]):
        v = int(token[2:], 16)
    elif("0b" == token[:2]):
        v = int(token[2:], 2)
    elif(token[0] == "'" and token[-1] == "'"):
        l = token[1:-1]
        if(len(l) == 2 and l[1] in dict_ecs_seq):
            v = ord(dict_ecs_seq[l[1]])
        else:
            try:
                v = ord(l)
            except TypeError:
                status_code = 4
                v = 0
    else:
        try:
            v = int(token)
        except ValueError:
            status_code = 2
            v = 0
    return v

def set_value_variable(value, addr=None, name=None):
    global status_code
    status_code = 0
    if(addr != None):
        r = [e[0] for e in name_table].index(addr)
        name_table[r][3] = value
    elif(name != None):
        r = [e[1] for e in name_table].index(name)
        name_table[r][3] = value

def do_named_proc(parsed_data, index, token):
    global status_code
    status_code = 0
    r = [e[1] for e in name_table].index(token)
    addr, name, _type, value = name_table[r]
    #debug(f"{addr=} {name=} {_type} {value=}")
    if(_type == TypeVariable.VARIABLE):
        push(value)
    elif(_type == TypeVariable.ARRAY):
        push(addr)
    else:
        global return_token_indexes
        return_token_indexes.append(index)
        return value
    return index + 1


def set_array(parsed_data, index):
    global status_code
    status_code = 0
    array_name = parsed_data[index + 1]
    i = pop()
    if(
        (not array_name.isdigit())
        and (array_name not in [e[1] for e in name_table])):
        if(0 < i):
            a = [0 for _ in range(i)]
            name_table.append(
                [id(a), array_name, TypeVariable.ARRAY, a]
            )
        else:
            status_code = 5
    elif(array_name in [e[1] for e in name_table]):
        value = pop()
        r = [e[1] for e in name_table].index(array_name)
        if(name_table[r][2] == TypeVariable.ARRAY):
            if(0 <= i < len(name_table[r][3])):
                name_table[r][3][i] = value
            else:
                status_code = 3
        else:
            a = [0 for _ in range(i)]
            name_table[r][0] = id(a)
            name_table[r][2] = TypeVariable.ARRAY
            name_table[r][3] = a
    return index + 2
    

def get_array(parsed_data, index):
    global status_code
    status_code = 0
    i = pop()
    array_name = parsed_data[index + 1]
    if(array_name in [e[1] for e in name_table]):
        r = [e[1] for e in name_table].index(array_name)
        if(0 <= i < len(name_table[r][3])):
            push(name_table[r][3][i])
        else:
            status_code = 3
    return index + 2

def set_variable(parsed_data, index):
    global status_code
    status_code = 0
    variable_name = parsed_data[index + 1]
    v = pop()
    if(variable_name not in [e[1] for e in name_table]):
        name_table.append(
            [id(v), variable_name, TypeVariable.VARIABLE, v]
        )
    else:
        r = [e[1] for e in name_table].index(variable_name)
        if(name_table[r][2] == TypeVariable.VARIABLE):
            set_value_variable(v, name=variable_name)
        else:
            name_table[r][0] = id(v)
            name_table[r][2] = TypeVariable.VARIABLE
            name_table[r][3] = v
    return index + 2

def calc_add(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(a + b)
    return index + 1


def calc_sub(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(a - b)
    return index + 1
    
def calc_mul(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(a * b)
    return index + 1
    
def calc_div(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    if(b != 0):
        push(a // b)
    else:
        push(0)
        status_code = 6
    return index + 1
    
def calc_mod(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    if(b != 0):
        push(a % b)
    else:
        push(0)
        status_code = 6
    return index + 1
    
def calc_and(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(a & b)
    return index + 1
    
def calc_or(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(a | b)
    return index + 1
    
def calc_xor(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(a ^ b)
    return index + 1
    
def calc_not(parsed_data, index):
    global status_code
    status_code = 0
    a = pop()
    push(~a)
    return index + 1
    
def cmp_lt(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(1 if a < b else 0)
    return index + 1
    
def cmp_equ(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(1 if a == b else 0)
    return index + 1
    
def cmp_gt(parsed_data, index):
    global status_code
    status_code = 0
    b = pop()
    a = pop()
    push(1 if a > b else 0)
    return index + 1
    
def reverse_bool(parsed_data, index):
    global status_code
    status_code = 0
    a = pop()
    push(1 if a == 0 else 0)
    return index + 1

def put_char(parsed_data, index):
    global status_code
    status_code = 0
    v = pop()
    sys.stdout.write(chr(v))
    return index + 1

def put_int(parsed_data, index):
    global status_code
    status_code = 0
    v = pop()
    sys.stdout.write(str(v))
    return index + 1

def put_hex(parsed_data, index):
    global status_code
    status_code = 0
    v = pop()
    sys.stdout.write(f"{v:x}")
    return index + 1

def put_bin(parsed_data, index):
    global status_code
    status_code = 0
    v = pop()
    sys.stdout.write(f"{v:b}")
    return index + 1

def print_string(parsed_data, index):
    global status_code
    status_code = 0
    addr = pop()
    if(addr in [e[0] for e in name_table]):
        i = [e[0] for e in name_table].index(addr)
        s = name_table[i][3]
        sys.stdout.write("".join([chr(c) for c in s]))
    return index + 1

def randint(parsed_data, index):
    global status_code
    status_code = 0
    a = data_stack.pop()
    x = random.randint(0, a)
    push(x)
    return index + 1

def calc_abs(parsed_data, index):
    global status_code
    status_code = 0
    push(abs(pop()))
    return index + 1

def get_code(parsed_data, index):
    global status_code
    push(status_code)
    status_code = 0
    return index + 1

def input_char(parsed_data, index):
    global input_buffer
    global status_code
    status_code = 0
    if(len(input_buffer) == 0):
        try:
            input_buffer = input() + "\0"
        except KeyboardInterrupt:
            return index + 1
    c = ord(input_buffer[0])
    input_buffer = input_buffer[1:]
    push(c)
    return index + 1
    

def dup_tos(parsed_data, index):
    global status_code
    status_code = 0
    v = pop()
    push(v)
    push(v)
    return index + 1

def rem_tos(parsed_data, index):
    global status_code
    status_code = 0
    pop()
    return index + 1

def cond_left(parsed_data, index):
    global status_code
    status_code = 0
    a = pop()
    if(a == 0):
        index = jump_table[index]
    else:
        index += 1
    return index
    

def cond_right(parsed_data, index):
    global status_code
    status_code = 0
    return index + 1

def jump_left(parsed_data, index):
    global status_code
    status_code = 0
    index = jump_table[index]
    return index

def jump_right(parsed_data, index):
    global status_code
    status_code = 0
    return index + 1

def loop_right(parsed_data, index):
    global status_code
    status_code = 0
    return index + 1
    

def loop_left(parsed_data, index):
    global status_code
    status_code = 0
    index = jump_table[index]
    return index
    

def start_subroutine(parsed_data, index):
    global status_code
    status_code = 0
    j = index
    subroutine_name = parsed_data[index + 1]
    if(subroutine_name not in [e[1] for e in name_table]):
        name_table.append(
            [index, subroutine_name, TypeVariable.SUBROUTINE, index + 2]
        )
    else:
        r = [e[1] for e in name_table].index(subroutine_name)
        name_table[r][0] = index
        name_table[r][2] = TypeVariable.SUBROUTINE
        name_table[r][3] = index + 2
    while(parsed_data[j] != ";"):
        j += 1
    return j + 1
    
    
def set_subroutine(parsed_data, index):
    global return_token_indexes
    global status_code
    status_code = 0
    if(len(return_token_indexes) != 1):
        index = return_token_indexes.pop(-1) + 1
    else:
        index = len(parsed_data)
    return index
    

def show_stack(parsed_data, index):
    global data_stack
    global status_code
    status_code = 0
    s = " ".join([str(e) for e in data_stack])
    print(f"<{len(data_stack)}> {s}")
    return index + 1
    

def show_history(parsed_data, index):
    global status_code
    status_code = 0
    l = pop()
    l = l if 0 < l else 15
    x = len(history_index.history)
    for i in range(x - l, x):
        h = history_index.get(i)
        if(h != None):
            print(f"[{i - x + 1}]({parsed_data[h]})")
        else:
            break
    return index + 1

def pause_program(parsed_data, index):
    global status_code
    status_code = 0
    try:
        input()
    except KeyboardInterrupt:
        return len(parsed_data)
    return index + 1

def sleep_program(parsed_data, index):
    global status_code
    status_code = 0
    t = pop()
    time.sleep(t / 1000)
    return index + 1

def set_trace_line(parsed_data, index):
    global status_code
    global execute_option
    status_code = 0
    s = pop()
    execute_option[0] = s
    return index + 1

def set_limit_token(parsed_data, index):
    global status_code
    global execute_option
    status_code = 0
    c = pop()
    if(0 < c):
        execute_option[2] = c
    else:
        execute_option[2] = 50000
    return index + 1

def proc_string(parsed_data, index):
    global status_code
    status_code = 0
    token = parsed_data[index]
    next_token = parsed_data[index + 1]
    string_list = parse_with_esc_seq(token[1:-1])
    addr = id(string_list)
    if(next_token in [e[1] for e in name_table]):
        i = [e[1] for e in name_table].index(next_token)
        name_table[i][0] = addr
        name_table[i][2] = TypeVariable.ARRAY
        name_table[i][3] = string_list
        return index + 2
    elif(next_token not in builtin_cmd_token
        and next_token not in escape_cmd_token
        and strtoint(next_token) == 0
        and status_code == 2
        ):
        status_code = 0
        name_table.append(
            [addr, next_token, TypeVariable.ARRAY, string_list]
        )
        return index + 2
    else:
        name_table.append(
            [addr, None, TypeVariable.ARRAY, string_list]
        )
        push(addr)
    return index + 1

def parse_with_esc_seq(raw):
    is_ckey = False
    result_list = []
    dict_ecs_seq = {
        "\\":"\\", "\"":"\"", "\'":"\'",
        "a":"\a", "b":"\b", "f":"\f",
        "n":"\n", "r":"\r", "t":"\t",
        "v":"\v", "e":'\x1b', "0":"\0"
    }
    for i, e in enumerate(raw):
        c = e
        if(is_ckey):
            c = dict_ecs_seq[e]
            is_ckey = False
        elif("\\" == e):
            is_ckey = True
            continue
        result_list.append(ord(c))
    return result_list

class TypeVariable(Enum):
    VARIABLE = "VARIABLE"
    ARRAY = "ARRAY"
    SUBROUTINE = "SUBROUTINE"


builtin_cmd_token = {
    "@": set_array,
    "@s": set_array,
    "@g": get_array,
    "$": set_variable,
    "+": calc_add,
    "-": calc_sub,
    "*": calc_mul,
    "/": calc_div,
    "%": calc_mod,
    "&": calc_and,
    "|": calc_or,
    "^": calc_xor,
    "~": calc_not,
    "<": cmp_lt,
    "=": cmp_equ,
    ">": cmp_gt,
    "!": reverse_bool,
    ".": put_char,
    ".i": put_int,
    ".x": put_hex,
    ".b": put_bin,
    ".c": put_char,
    ".s": print_string,
    "\'\'": randint,
    "\"\"": calc_abs,
    ",": get_code,
    "?": input_char,
    "_": dup_tos,
    "`": rem_tos,
    "(": cond_left,
    ")": cond_right,
    "[": jump_left,
    "]": jump_right,
    "{": loop_right,
    "}": loop_left,
    ":": start_subroutine,
    ";": set_subroutine,
}

escape_cmd_token = {
    "\\dstack": show_stack,
    "\\dhistory": show_history,
    
    "\\pause": pause_program,
    "\\sleep": sleep_program,
    
    "\\tracetoken": set_trace_line,
    "\\limittoken": set_limit_token, 
}

data_stack = []

jump_table = {}

macro_table = {}

# variable name table
# VARIABLE: id, name, VARIABLE, value
# ARRAY: id, name, ARRAY, [0; n]
# SUBROUTINE: index, name, SUBROUTINE, index+2
name_table = []

return_token_index = -1
return_token_indexes = [-1, ]
history_index = None

status_code = 0

input_buffer = ""

execute_option = [0, 0, 250000]

class History_token_index():
    def __init__(self, length=100):
        self.history = [None for _ in range(length)]
    def push(self, index):
        self.history.pop(0)
        self.history.append(index)
    def get(self, i):
        return self.history[i]


if __name__ == "__main__":
    file_name = sys.argv[1]
    parsed_data = parse_source_code(sys.argv[1])
    jump_table = make_jump_table(parsed_data)
    execute_code = 0
    history_index = History_token_index()
    index = 0
    while 0 <= index and index != len(parsed_data):
        history_index.push(index)
        index = execute(parsed_data, index, execute_code)
        

