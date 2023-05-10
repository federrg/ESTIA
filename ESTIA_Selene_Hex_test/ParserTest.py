import sys
import argparse

parser = argparse.ArgumentParser(description='Test the rotation range of the ESTIA Selene guides')
parser.add_argument('--top',
                    default=None,
                    action='store_true',     
                    help='Test all the mirrors of the top section (default test all mirrors)')
parser.add_argument('--bottom', 
                    default=None,
                    action='store_true',     
                    help='Test all the mirrors of the bottom section (default test all mirrors)')

parser.add_argument('-m', '--manual', 
                    default=False, 
                    action='store_true',     
                    help='Activate manual mode')

args = parser.parse_args()
print(args.top, args.bottom, args.manual)


def manualMode(manual=args.manual, skipPosition=False):
    if manual and skipPosition:
        key=input("Press ENTER to continue or s to skip this position: ")
        if key == '':
            return False
        elif key == 's' or key =='S':
            return True
    elif manual and not skipPosition:
        input('"Press ENTER to continue...')
        return
    else:
        return

for i in range(10):
    print(f'starting {i}')
    if manualMode(skipPosition=True):
        i=i+1        
    else:
        print(f'finishing {i}')

print('End of test')