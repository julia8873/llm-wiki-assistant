
with open('moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/sync_worker/tasks.py', 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

out = []
in_sync = False
in_teacher = False
for i, l in enumerate(lines):
    if 'async with distributed_repo_lock(destino_local):' in l:
        out.append(l)
        if 'sync_repo_task' in lines[i-5] or 'sync_repo_task' in lines[i-4]:
            in_sync = True
        elif 'init_teacher_repo_task' in lines[i-5] or 'init_teacher_repo_task' in lines[i-4]:
            in_teacher = True
        continue
    
    if in_sync and l == '    except Exception as e:':
        in_sync = False
    if in_teacher and l == '    except Exception as e:':
        in_teacher = False
        
    if in_sync or in_teacher:
        if l.startswith('        ') and not l.startswith('            '):
            out.append('    ' + l)
        elif l.startswith(''):
            out.append(l if not l.strip() else '    ' + l)
    else:
        out.append(l)

with open('moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/sync_worker/tasks.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

