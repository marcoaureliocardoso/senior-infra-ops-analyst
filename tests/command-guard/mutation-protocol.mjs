export function interpretWitnessResult(result, id, phase) {
  if (!['baseline', 'mutant'].includes(phase)) throw new Error(`${id}: unknown witness phase`);
  if (phase === 'baseline') {
    if (result.status === 0 && result.stderr === '') return 'passed';
    throw new Error(`${id}: pristine witness did not pass cleanly`);
  }
  if (result.status === 42 && result.stderr === `WITNESS_ASSERTION:${id}\n`) return 'killed';
  throw new Error(`${id}: mutant did not fail through its matching semantic assertion`);
}
