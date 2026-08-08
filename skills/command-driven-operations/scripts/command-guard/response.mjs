export function decisionResponse(result) {
  if (!['allow', 'ask', 'deny'].includes(result.decision)) throw new Error('invalid decision');
  const response = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: result.decision,
      permissionDecisionReason: result.message,
    },
  };
  if (result.decision === 'deny') response.systemMessage = result.message;
  return response;
}
