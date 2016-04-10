"""
Author      :   Vlad Glv, 2016
Revision    :   1.0, Basic tool to analyze frame times and their consistency
                1.1, Migration to Python 3.x
                1.2, Improved coding style
"""
# Requires Python 3.5.1

# import cProfile
import csv
import math
import os
import sys

# Help segment of the program
Syntax_Help = """{0} fraps_frametimes_csv stutter_margin=2.0 [ms]
log_out_file_name=stdout'"""

# Range of accepted stutter margin values
Stutter_Margin_Min = 0.10
Stutter_Margin_Max = 10.1

# Smoothness rating used to evaluate the consistency of analyzed samples
# This is a log2 scale of the percentage of frames having a variance above a
# set stutter margin

# Version of the rating to allow consistent comparison of results
SR_Version = 3

# Minimum percentage of frames producing stutter
SR_Min = 0.124
# Maximum percentage of frames producing stutter
SR_Max = 100.1

# Verbal rating for percentage of smooth frames
SR_Verbal = [
    'Practically Impossible',
    'Perfect',
    'Excellent',
    'Very Good',
    'Good',
    'Average',
    'Below Average',
    'Mediocre',
    'Atrocious',
    'Abysmal'
]


# Returns the extension of 'ss' or 'ss' otherwise
def remove_extension(ss: str) -> str:
    try:
        return ss[0:ss.rindex('.')]
    except ValueError:
        return ss


# Returns the extension of 'ss' or an empty string otherwise
def get_extension(ss: str) -> str:
    try:
        return ss[ss.rindex('.') + 1:]
    except ValueError:
        return ''


# Returns a string representing the reformatted float 'f' with 'n' digits
def fixed_precision(f: float, n: int) -> str:
    fmt = '{1}:.{0}f{2}'.format(n, '{', '}')
    return fmt.format(f)


# Clamps the value between 'min_value' and 'max_value'
def clamp(value, min_value, max_value):
    assert min_value <= max_value

    return max(min(value, max_value), min_value)


# Binary select on 'expr' between 'true_' and 'false_' and return the result
def binary_select1(expr, true_, false_):
    if expr:
        return true_

    return false_


# Recomputes a new average including a new inserted sample
# n must be n >= 0
def moving_average(avg: float, x: float, n: int) -> float:
    assert n >= 0

    if n >= 0:
        return (x + n * avg) / (n + 1)


# Prints a string 'str' to a file 'f'
def fprintf(s: str, f):
    print(s, file = f)


def analyze(name = '', stutter_margin = 2.0, rout = sys.stdout):
    # Open the csv file and read it
    with open(name, 'r') as fin:
        reader = csv.reader(fin, delimiter = ',')
        contents = []

        # Convert string data to numerical data on the fly while removing extra
        # spaces
        for row in reader:
            irow = []
            for e_ in row:
                irow.append(binary_select1('m' in e_, e_, e_.replace(' ', '')))

            if 'Frame' not in irow[0]:
                contents.append([int(irow[0]), float(irow[1])])
            else:
                contents.append(irow)

        # Test if the header is correct and expected
        if contents[0][0] != 'Frame' or contents[0][1] != ' Time (ms)':
            fprintf('ERROR: Unexpected headers!', rout)
            return

        # Append new columns
        contents[0].append(' Frame Time (ms)')
        contents[0].append(' Frame Rate (fps)')
        contents[0].append(' Frame Deltas (ms)')
        contents[0].append(' Extra Time (ms)')
        contents[0].append(' Visible Stutter (b)')

        # Values for the first set of values
        for i in range(0, 5):
            contents[1].append(0)

        # Variables used for smoothness, stutter and extra time computation
        stutter_samples = 0
        smooth_samples = 0
        extra_total_time = 0
        fps_large_const = 90000.0
        fps_min = fps_large_const
        fps_avg = 0.0
        fps_avg_smooth = 0.0
        fps_max = 0.0

        # Computation of five extra rows
        for i in range(2, len(contents)):
            # Save previous and current values
            prev = contents[i - 1]
            curr = contents[i]

            # Compute needed values
            frame_time = curr[1] - prev[1]
            frame_rate = 1000 / frame_time
            frame_delta = frame_time - prev[2]

            extra_time_val = abs(frame_delta) - stutter_margin
            extra_time = binary_select1(extra_time_val > 0, extra_time_val, 0)
            visible_stutter = binary_select1(extra_time_val > 0, 1, 0)

            sample_n = i - 2

            # Count samples of each type
            if visible_stutter == 1:
                stutter_samples += 1
                extra_total_time += extra_time_val
                fps_avg_smooth = moving_average(fps_avg_smooth, 0.0, sample_n)
            else:
                smooth_samples += 1
                fps_avg_smooth = \
                    moving_average(fps_avg_smooth, frame_rate, sample_n)

            # Compute fps metrics
            assert frame_rate < fps_large_const
            fps_max = max(frame_rate, fps_max)
            fps_min = min(frame_rate, fps_min)
            fps_avg = moving_average(fps_avg, frame_rate, sample_n)

            # Add the data to the contents of the csv
            curr.append(frame_time)
            curr.append(frame_rate)
            curr.append(frame_delta)
            curr.append(extra_time)
            curr.append(visible_stutter)

    # Compute overall parameters of analyzed samples
    total_samples = stutter_samples + smooth_samples
    overall_smoothness = smooth_samples * 100.0 / total_samples
    overall_stutter = stutter_samples * 100.0 / total_samples
    overall_extra_time = extra_total_time * 100.0 / contents[-1][1]
    overall_fps_avg_diff_ns = (fps_avg_smooth / fps_avg - 1.0) * 100.0

    # Print results to rout
    fprintf('<Results>', rout)
    fprintf('\tStutter margin\t: {0:.3f} [ms]'.format(stutter_margin), rout)
    fprintf('\n\tFrame Rate Min\t: {0:.3f} [fps]'.format(fps_min), rout)
    fprintf('\tFrame Rate Max\t: {0:.3f} [fps]'.format(fps_max), rout)
    fprintf('\tFrame Rate Avg Normal [N]\t: {0:.3f} [fps]'.format(fps_avg),
            rout)
    fprintf('\tFrame Rate Avg Smooth [S]\t: {0:.3f} [fps]'
            .format(fps_avg_smooth), rout)
    fprintf('\tFrame Rate Avg Diff[N, S]\t: {0:.3f}%'
            .format(overall_fps_avg_diff_ns), rout)
    fprintf('\n\tStutter samples\t: {0}'.format(stutter_samples), rout)
    fprintf('\tSmooth samples\t: {0}'.format(smooth_samples), rout)
    fprintf('\tTotal samples\t: {0}'.format(total_samples), rout)
    fprintf('\tExtra time\t: {0:.3f} [ms]'.format(extra_total_time), rout)
    fprintf('\tTotal time\t: {0:.3f} [ms]'.format(contents[-1][1]), rout)
    fprintf('\n\tOverall smoothness\t: {0:.3f}%'.format(overall_smoothness),
            rout)
    fprintf('\tOverall stutter\t\t: {0:.3f}%'.format(overall_stutter), rout)
    fprintf('\tOverall extra time\t: {0:.3f}%'.format(overall_extra_time), rout)

    # Print the smoothness rating to rout
    ovc = clamp(overall_stutter, SR_Min, SR_Max)
    rmax = len(SR_Verbal)
    rc = clamp(int(math.ceil(math.log(ovc, 2))) + 3, 0, rmax)
    rs_ = '\tOverall rating<v:{0}>\t: {1}, {2} of {3}\n'
    fprintf(rs_.format(SR_Version, SR_Verbal[rc], rmax - rc, rmax), rout)

    # Write the analyzed CSV
    out_name = remove_extension(name) + '_fpa.' + get_extension(name)
    with open(out_name, 'w', encoding = "utf-8") as fout:
        writer = csv.writer(fout, delimiter = ',')
        writer.writerows(contents)

    print('<Info>\tAnalysis completed')


# cProfile.run('analyze("sample.csv")')
if __name__ == "__main__":
    try:
        # One parameter -> Name of the file to analyze
        if len(sys.argv) == 2:
            analyze(sys.argv[1])
        # Two parameters -> Name of the file to analyze, Stutter margin
        elif len(sys.argv) == 3:
            sm = float(sys.argv[2])
            if Stutter_Margin_Min < sm < Stutter_Margin_Max:
                analyze(sys.argv[1], sm)
            else:
                print('stutter_margin should be on ]{0}, {1}['
                      .format(Stutter_Margin_Min, Stutter_Margin_Max))
        # Three parameters -> Name of the file to analyze, Stutter margin,
        # Results file name
        elif len(sys.argv) == 4:
            sm = float(sys.argv[2])
            if Stutter_Margin_Min < sm < Stutter_Margin_Max:
                analyze(sys.argv[1], sm, open(sys.argv[3], 'w'))
            else:
                print('stutter_margin should be on ]{0}, {1}['
                      .format(Stutter_Margin_Min, Stutter_Margin_Max))
        # Less than one parameter -> Print help
        else:
            print(Syntax_Help.format(os.path.basename(sys.argv[0])))

    except ValueError:
        print('<Error>\tInvalid parameter "stutter_margin"')
        print(Syntax_Help.format(sys.argv[0]))

    except IOError as e:
        print("<Error>\t{0} '{1}'".format(e.strerror, e.filename))

    except Exception as e:
        print("<Error>\t{0}".format(e.args[0]))
