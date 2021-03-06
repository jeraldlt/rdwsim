import pathlib
import sys
from math import *
import pandas as pd

def heading_difference(heading1, heading2):
    if heading1 * heading2 > 0:
        return abs(heading2 - heading1)

    if heading1 < 0:
        heading1 += 2 * pi
    elif heading2 < 0:
        heading2 += 2 * pi

    return abs(heading2 - heading1)


def path_time(path_df, window_size):
    """Calculates the total time taken for the user to complete the task"""
    return path_df[['deltaFrameTime']].sum().item()

def path_rotation(path_df, head_body_sep, window_size):
    """Calculates the total rotation in degrees and mean rotational velocity in degrees/sec for a path"""

    # total_time = path_time(path_df, window_size)

    count = 0
    rotation = 0.0
    velocities = 0.0

    if head_body_sep:
        data = path_df[["virtualHeading", "deltaFrameTime"]]

        last_row = None
        for i, row in data.iterrows():
            if i == 0:
                last_row = row
                continue
            elif i == 1:
                last_row = row
                continue

            delta_rotation = abs(row['virtualHeading'] - last_row['virtualHeading']).item()
            
            rotation += delta_rotation
            velocities += delta_rotation / row['deltaFrameTime'].item()
            last_row = row
            count += 1


    else:
        data = path_df[["virtualX", "virtualY", "deltaFrameTime"]].rolling(window_size, min_periods=1, center=True).mean()

        heading = 0.0
        last_row = None

        for i, row in data.iterrows():
            if i == 0:
                last_row = row
                continue
            elif i == 1:
                heading = atan2(row['virtualY'] - last_row['virtualY'], row['virtualX'] - last_row['virtualX'])
                last_row = row
                continue

            new_heading = atan2(row['virtualY'] - last_row['virtualY'], row['virtualX'] - last_row['virtualX'])

            delta_rotation = degrees(heading_difference(heading, new_heading))
            
            if sqrt(pow(row['virtualY'] - last_row['virtualY'], 2) + pow(row['virtualX'] - last_row['virtualX'], 2)) < 1e-10:
                # print(i, heading, new_heading, delta_rotation, row['virtualY'] - last_row['virtualY'], row['virtualX'] - last_row['virtualX'])
                last_row = row
                heading = new_heading
                continue

            rotation += delta_rotation
            velocities += delta_rotation / row['deltaFrameTime'].item()

            count += 1
            heading = new_heading
            last_row = row

    return rotation, (velocities / count)

def path_translation(path_df):
    # total_time = path_time(path_df, 1)

    translation = 0.0
    velocities = 0.0
    data = path_df[["virtualX", "virtualY", "deltaFrameTime"]]

    last_row = None
    for i, row in data.iterrows():
        if i == 0:
            last_row = row
            continue
        elif i == 1:
            last_row = row
            continue

        delta_translation = sqrt(pow(row['virtualY'] - last_row['virtualY'], 2) + pow(row['virtualX'] - last_row['virtualX'], 2))
        translation += delta_translation
        velocities += delta_translation / row['deltaFrameTime'].item()
        last_row = row

    return translation, (velocities / len(data))


def compute_environment(environment, window_size):
    if environment == "constrained":
        paths = pathlib.Path('./paths/constrained/').glob('*.txt')
    elif environment == "opensearch":
        paths = pathlib.Path('./paths/opensearch/').glob('*.txt')
    else:
        print(f'Unknown environment: {environment}', file=sys.stderr)
        sys.exit(1)


    csv = []
    
    for f in paths:
        path_df = pd.read_csv(f, sep='\t') 
       
        total_time = path_time(path_df, window_size)

        rotation_sep, rotation_velocity_sep = path_rotation(path_df, True, window_size)
        rotation_nosep, rotation_velocity_nosep = path_rotation(path_df, False, window_size)
        rotation_standard = 90.0

        # print(rotation_velocity_sep)

        translation, translation_velocity = path_translation(path_df)
        translation_standard = 1.0

        path_data = {}

        path_data["environment"] = environment
        path_data["path"] = f
        path_data["total_time"] = total_time
        path_data["total_translation"] = translation
        path_data["mean_translation_velocity"] = translation_velocity
        path_data["standard_translation_velocity"] = translation_standard
        path_data["total_rotation_sep"] = rotation_sep
        path_data["total_rotation_nosep"] = rotation_nosep
        path_data["mean_rotation_velocity_sep"] = rotation_velocity_sep
        path_data["mean_rotation_velocity_nosep"] = rotation_velocity_nosep
        path_data["standard_rotation_velocity"] = rotation_standard


        # Translaton gain
        path_data["translation_mean"] = (translation_velocity * total_time) / translation
        path_data["translation_standard"] = (translation_standard * total_time) / translation

        # Rotation gain with head-body separation
        path_data["rotation_mean_sep"] = (rotation_velocity_sep * total_time) / rotation_sep
        path_data["rotation_standard_sep"] = (rotation_standard * total_time) / rotation_sep
        
        # Rotation gain without head-body separation
        path_data["rotation_mean_nosep"] = (rotation_velocity_nosep * total_time) / rotation_nosep
        path_data["rotation_standard_nosep"] = (rotation_standard * total_time) / rotation_nosep

        # print(environment, rotation_standard, total_time, rotation_sep, path_data["rotation_standard_sep"])
        # Combined rotation and curvature gains
        constant_availability = 0.0
        mean_availability = 0.0
        dynamic_availability = 0.0
        rotation_gain = 1.4
        curvature = 1 / 7.5
        rotation = 0.0
        
        last_row = None
        for i, row in path_df.iterrows():
            if i == 0:
                last_row = row
                continue

            rotation += abs(row['virtualHeading'] - last_row['virtualHeading'])

            dt = row['deltaFrameTime'].item()
            delta_rotation = abs(row['virtualHeading'] - last_row['virtualHeading']).item()
            delta_translation = sqrt(pow(row['virtualY'] - last_row['virtualY'], 2) + pow(row['virtualX'] - last_row['virtualX'], 2))

            constant_availability += max(abs(rotation_standard * dt * (rotation_gain - 1.0)), abs(translation_standard * dt * curvature))
            mean_availability += max(abs(rotation_velocity_sep * dt * (rotation_gain - 1.0)), abs(translation_velocity * dt * curvature))
            dynamic_availability += max(abs(delta_rotation * (rotation_gain - 1.0)), abs(delta_translation * curvature))
        
            last_row = row
       
        if dynamic_availability > 0:
            path_data["combined_standard_nosep"] = constant_availability / dynamic_availability
            path_data["combined_mean_nosep"] = mean_availability / dynamic_availability
            path_data["combined_dynamic_nosep"] = dynamic_availability


        csv.append(path_data)

    return csv


if __name__ == '__main__':
    csv = []

    csv += compute_environment("constrained", 10)
    csv += compute_environment("opensearch", 10)

    df = pd.DataFrame(csv)
    df.to_csv("data.csv", index=False)
