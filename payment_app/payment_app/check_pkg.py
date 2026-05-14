import sys, importlib
with open('diagnostic.txt', 'w') as f:
    f.write('exe=' + sys.executable + '\n')
    f.write('find_spec=' + repr(importlib.util.find_spec('pkg_resources')) + '\n')
    try:
        import pkg_resources
        f.write('pkg=' + pkg_resources.__file__ + '\n')
    except Exception as e:
        f.write('error=' + repr(e) + '\n')
print('done')
