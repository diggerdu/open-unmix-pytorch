import argparse
import musdb
import museval
import test
import multiprocessing
import functools
from pathlib import Path


def separate_and_evaluate(
    track,
    models,
    niter,
    alpha,
    softmask,
    final_smoothing,
    output_dir
):
    print(track.name, track.duration)
    estimates = test.separate(
        audio=track.audio,
        models=models,
        niter=niter,
        alpha=alpha,
        softmask=softmask,
        final_smoothing=final_smoothing
    )
    if args.outdir:
        mus.save_estimates(estimates, track, args.outdir)

    if args.evaldir is not None:
        scores = museval.eval_mus_track(
            track, estimates, output_dir=args.evaldir
        )
        print(scores)
        return scores


if __name__ == '__main__':
    # Training settings
    parser = argparse.ArgumentParser(
        description='MUSDB18 Evaluation',
        add_help=False
    )

    parser.add_argument(
        '--targets',
        nargs='+',
        default=['vocals', 'drums', 'bass', 'other'],
        type=str,
        help='provide targets to be processed. \
              If none, all available targets will be computed'
    )

    parser.add_argument(
        '--modeldir',
        type=str,
        help='path to mode base directory of pretrained models'
    )

    parser.add_argument(
        '--modelname',
        choices=['Unmix16kBLSTMStereo'],
        default='Unmix16kBLSTMStereo',
        type=str,
        help='use pretrained model'
    )

    parser.add_argument(
        '--outdir',
        type=str,
        default="OSU_RESULTS",
        help='Results path where audio evaluation results are stored'
    )

    parser.add_argument(
        '--evaldir',
        type=str,
        help='Results path for museval estimates'
    )

    parser.add_argument(
        '--root',
        type=str,
        help='Path to MUSDB18'
    )

    parser.add_argument(
        '--subset',
        type=str,
        help='MUSDB subset (`train`/`test`)'
    )

    parser.add_argument(
        '--cores',
        type=int,
        default=1
    )

    args, _ = parser.parse_known_args()
    args = test.inference_args(parser, args)

    if args.modeldir:
        models = test.load_models(args.modeldir, args.targets)
        model_name = Path(args.modeldir).stem
    else:
        import hubconf
        pretrained_model = getattr(hubconf, args.modelname)
        models = {
            target: pretrained_model(target=target, device=test.device)
            for target in args.targets
        }
        model_name = args.modelname

    mus = musdb.DB(root=args.root, download=False, subsets=args.subset)
    if args.cores > 1:
        pool = multiprocessing.Pool(args.cores)
        results = list(
            pool.imap_unordered(
                func=functools.partial(
                    separate_and_evaluate,
                    models=models,
                    niter=args.niter,
                    alpha=args.alpha,
                    softmask=args.softmask,
                    final_smoothing=args.final_smoothing,
                    output_dir=args.evaldir
                ),
                iterable=mus.tracks,
                chunksize=1
            )
        )

        pool.close()
        pool.join()
    else:
        for track in mus.tracks:
            separate_and_evaluate(
                track,
                models=models,
                niter=args.niter,
                alpha=args.alpha,
                softmask=args.softmask,
                final_smoothing=args.final_smoothing,
                output_dir=args.evaldir
            )
