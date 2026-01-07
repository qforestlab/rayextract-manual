import os
import pandas as pd
import argparse


def read_rayextract_treefile(path):
    """Read a rayextract treefile.

    Behavior:
    - If the file has exactly 3 lines (comment, header, data) it returns a single DataFrame for the one tree.
    - If it has more data lines (multiple trees) it returns a list of DataFrames, one per tree.

    Parsing rules:
    - If the header line contains a space character this is treated as a separator between per-tree attributes (the
      first chunk) and per-segment attributes (the remaining chunk). All headers up to the first space are skipped and
      the corresponding first space-separated data chunk is skipped as well.
    - If the header line does not contain a space, all headers are used (no skipping).
    """
    # Read the file and ignore empty lines
    with open(path, 'r') as file:
        lines = [l for l in (ln.rstrip('\n') for ln in file.readlines()) if l.strip()]

    if len(lines) < 3:
        raise ValueError("File must contain at least 3 non-empty lines: comment, header, data")

    header_line = lines[1]
    headers = [h.strip() for h in header_line.strip().split(',') if h.strip()]
    data_lines = [l.strip() for l in lines[2:] if l.strip()]

    def _parse_one_data_line(data_line):
        # split into space-separated rows, stripping trailing commas from each
        rows = [row.rstrip(',') for row in data_line.split(' ') if row.strip()]

        # If header_line contains a space, treat it as a separator between per-tree and per-segment headers
        if ' ' in header_line:
            # headers up to the first space (prefix) are skipped
            idx = header_line.find(' ')
            prefix_headers = [h.strip() for h in header_line[:idx].split(',') if h.strip()]
            skip_n = len(prefix_headers)
            seg_headers = headers[skip_n:]
            # skip the corresponding first space-separated data chunk (per-tree attributes)
            seg_rows = rows[1:]
        else:
            seg_headers = headers
            seg_rows = rows

        # Parse each segment row (comma-separated values) into floats (robust to missing values)
        parsed = []
        for r in seg_rows:
            parts = [p for p in r.split(',') if p != '']
            row_vals = []
            for p in parts:
                try:
                    row_vals.append(float(p))
                except ValueError:
                    # preserve NaNs for non-parsable values
                    row_vals.append(float('nan'))
            parsed.append(row_vals)

        df = pd.DataFrame(parsed, columns=seg_headers)
        return df

    parsed_dfs = [_parse_one_data_line(dl) for dl in data_lines]

    # If original file had exactly 3 lines (single tree), return single DataFrame, else return list
    if len(lines) == 3:
        return parsed_dfs[0]
    return parsed_dfs


def make_treefiles_dataframe(treefile_dir, df_out):
    ''' makes a dataframe with columns 'filename, tree id, x-coordinate first cylinder, 
        y-coordinate first cylinder, diameter, selection status (default = undecided)' 
    '''
    # Loop over all treefiles in directory
    data = []
    for treefile in os.listdir(treefile_dir):
        # Get tree index from filename
        idx = int(treefile[:-4].split('_')[-1])

        # Read treefile into dataframe
        df = read_rayextract_treefile(os.path.join(treefile_dir, treefile))

        # Store name. id, base coordinates and radius
        data.append({
            'filename': treefile,
            'id': idx,
            'x': df['x'][0],
            'y': df['y'][0],
            'd': df['radius'][0] * 2,
            'selection': 'undecided',
        })

    # Convert to pandas dataframe and store as CSV
    df = pd.DataFrame(data)
    df = df.sort_values(by=['id'])
    return df.to_csv(df_out, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Make csv dataframe with all treenames and attributes")
    parser.add_argument("dir_treefile", help="Directory containing treefiles")
    parser.add_argument("df_out", help="Path to dataframe.csv ")
    args = parser.parse_args()

    make_treefiles_dataframe(args.dir_treefile, args.df_out)