from absl import app
from absl import flags
from absl import logging as log
from dance import Dances, Dance
from dancer import Dancers, Dancer
from matching import match_dancers
import pandas as pd

flags.DEFINE_string("quotas", None, "Filename associated with dance quotas.")
flags.DEFINE_string("dance_scores", None,
                    "Filename associated with dancer scores.")
flags.DEFINE_string(
    "dancer_rankings", None,
    "Filename associated with dancer info and dancer rankings.")

FLAGS = flags.FLAGS


def create_dancers(dancers_df):
    dancers = Dancers()
    for _, row in dancers_df.iterrows():
        dancers.add_dancer(Dancer.from_pandas_row(row))

    return dancers


def create_dances(quotas_df, dance_scores_df, dancers):
    dances = Dances()
    for _, row in quotas_df.iterrows():
        dance = Dance(row['dance'].strip(), int(row['quota']))
        dances.add_dance(dance)

    for _, row in dance_scores_df.iterrows():
        dance = row['dance'].strip()
        email = row['email'].strip().lower()
        dancer = dancers.get_dancer(email)

        if not dancer.preffed(dance):
            dancer.add_didnt_pref(dance)

        assert dance in dances, "Error. Dance with name %s not found in quotas file." % (
            dance)

        dances[dance].add_dancer(dancers[email], row['score'])

    for dance in dances:
        dance.ready()

    return dances


QUOTAS_COLUMN_NAMES = ["dance", "quota"]
DANCE_SCORES_COLUMN_NAMES = ["dance", "name", "email", "score"]
DANCER_COLUMN_NAMES = [
    "timestamp", "email", "name", "year", "gender", "tshirt_size",
    "first_choice", "second_choice", "third_choice", "nonauditions"
]


def main(argv):
    assert len(argv) == 1, "Unrecognized arguments"

    # Make sure the files are passed in.
    assert FLAGS.quotas, "Must pass in a quotas file using --quotas=<filename>. \
        See quotas file for the format of the quotas file."

    assert FLAGS.dance_scores, "Must pass in a dance scores file using, \
        --dance_scores=<filename>. See dance_scores file for the format of the \
                dance_scores file."

    assert FLAGS.dancer_rankings, "Must pass in a dancer_rankings file using \
        --dancer_rankings=<filename>. See dancer_rankings file for the format of the \
        dance_scores file."

    # Load in all the files.
    quotas_df = pd.read_csv(FLAGS.quotas,
                            names=QUOTAS_COLUMN_NAMES,
                            keep_default_na=False,
                            index_col=False)
    dance_scores_df = pd.read_csv(FLAGS.dance_scores,
                                  names=DANCE_SCORES_COLUMN_NAMES,
                                  keep_default_na=False,
                                  index_col=False)
    dancer_rankings_df = pd.read_csv(FLAGS.dancer_rankings,
                                     names=DANCER_COLUMN_NAMES,
                                     keep_default_na=False,
                                     index_col=False)

    # Make the data in an easier to work with format.
    dancers = create_dancers(dancer_rankings_df)
    dances = create_dances(quotas_df, dance_scores_df, dancers)

    log.info(
        "Done loading dances and dancers into memory. Running matching algorithm now..."
    )

    matchings = match_dancers(dancers, dances, False)

    print("Matches created:", dances)
    log.info("Done matching dancers to dances. Generating output files...")

    for k, v in matchings.items():
        dancers_matched = [dancers[x.name] for x in v]
        dances[k.name].set_matchings(dancers_matched)

        for dancer in dancers_matched:
            # Sanity check, first.
            if dancers[dancer.email].dance:
                print(
                    "%s may have been assigned to more than one dance. Is this a mistake?"
                )
            dancers[dancer.email].dance = k.name

    dancers.to_pandas_df().to_csv("matchings_by_dancer.csv")
    dances.to_pandas_df().to_csv("matchings_by_dance.csv")

    log.info("Find matchings by dancer in matchings_by_dancer.csv")
    log.info("Find matchings by dance in matchings_by_dance.csv")


if __name__ == "__main__":
    app.run(main)
