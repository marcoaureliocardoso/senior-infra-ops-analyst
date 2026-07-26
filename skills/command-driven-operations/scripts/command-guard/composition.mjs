export const GRAMMAR_PRODUCTIONS = Object.freeze(['stage', 'pipeline', 'and', 'or', 'sequence', 'redirect']);

export function buildComposition(lexed) {
  const stages = [];
  const operators = [];
  let words = [];
  let redirects = [];
  const flush = () => {
    if (!words.length) throw new Error('empty command stage');
    stages.push(Object.freeze({ index: stages.length + 1, argv: Object.freeze(words), redirects: Object.freeze(redirects), profile: lexed.profile }));
    words = []; redirects = [];
  };
  for (let index = 0; index < lexed.tokens.length; index += 1) {
    const token = lexed.tokens[index];
    if (token.kind === 'word') { words.push(token.cooked); continue; }
    if (token.kind === 'redirect') {
      const destination = lexed.tokens[index + 1];
      if (!destination || destination.kind !== 'word') throw new Error('redirection destination is missing');
      redirects.push({ operator: token.cooked, destination: destination.cooked });
      index += 1; continue;
    }
    flush(); operators.push(token.cooked);
  }
  flush();
  return Object.freeze({
    stages: Object.freeze(stages), operators: Object.freeze(operators),
    redirects: Object.freeze(stages.flatMap((stage) => stage.redirects)),
    edges: Object.freeze(operators.map((operator, index) => ({ from: index + 1, to: index + 2, operator }))),
  });
}
