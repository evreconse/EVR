Íimport os

total_size = 0
for dirpath, dirnames, filenames in os.walk('.'):
    for f in filenames:
        fp = os.path.join(dirpath, f)
        if os.path.exists(fp):
            total_size += os.path.getsize(fp)

print(f'Total size: {total_size / (1024*1024):.2f} MB')
print(f'Total size: {total_size / (1024*1024*1024):.2f} GB')
Í*cascade082Mfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/calculate_size.py