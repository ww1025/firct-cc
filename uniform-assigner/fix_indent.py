with open(r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

marker_start = '            with st.status("正在生成分配方案...", expanded=True):'
marker_end = 'elif st.session_state.page =='

start_idx = text.find(marker_start)
end_idx = text.find(marker_end, start_idx)

print('Start:', start_idx, 'End:', end_idx)

middle = text[start_idx:end_idx]
new_middle = []
for line in middle.split('\n'):
    if line.startswith('    '):
        new_middle.append(line[4:])
    else:
        new_middle.append(line)
fixed_middle = '\n'.join(new_middle)

text = text[:start_idx] + fixed_middle + text[end_idx:]

with open(r'C:\Users\夏瑞泽\Desktop\firct cc\uniform-assigner\app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done')
