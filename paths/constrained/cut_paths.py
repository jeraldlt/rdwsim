import pathlib

def distance(lines):
    dis = 0.0

    for i in range(2, len(lines)):
        x1 = float(lines[i-1].split('\t')[6])
        x2 = float(lines[i].split('\t')[6])
        y1 = float(lines[i-1].split('\t')[7])
        y2 = float(lines[i].split('\t')[7])
        
        dis += ( (x2 - x1) ** 2 + (y2 - y1) ** 2 ) ** 0.5
        
    return dis
    
total_distance = 0.0              

for f in pathlib.Path('../original_paths/constrained').glob('*.txt'):
    lines = [x for x in f.read_text().split('\n') if x]
    
    header = lines[0]
    paths = [[header]]
    
    for line in lines[1:]:
        line_values = [float(x) for x in line.split('\t') if x]
        x = line_values[6]
        y = line_values[7]
        
        if abs(x) < 12.0 and abs(y) < 19.0:
            paths[-1].append(line)
        else:
            if len(paths[-1]) > 1:
                paths.append([header])
    
    distances = []
    i = 0
    for path in paths:
        dis = distance(path)
        if dis >= 30.0:
            total_distance += dis
            fout = pathlib.Path(f"./{f.stem}_{i}{''.join(f.suffixes)}")
            fout.write_text('\n'.join(path))
            i += 1
    
print(total_distance)
