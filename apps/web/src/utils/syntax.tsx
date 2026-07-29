import React from "react";

/**
 * Parses raw code text and returns colorized React elements based on 
 * keywords, comments, strings, and punctuation tokens.
 */
export function highlightCode(text: string): React.ReactNode {
  const tokens: React.ReactNode[] = [];
  let remaining = text;
  
  // Handle single-line comments early
  if (text.includes("//") || text.includes("#")) {
    const commentChar = text.includes("//") ? "//" : "#";
    const parts = text.split(commentChar);
    const codePart = parts[0];
    const commentPart = parts.slice(1).join(commentChar);
    return (
      <>
        {highlightCode(codePart)}
        <span className="syntax-comment">{commentChar}{commentPart}</span>
      </>
    );
  }

  // Common keywords in JavaScript, Python, TypeScript, Java
  const keywordRegex = /\b(def|try|except|as|import|from|return|for|in|if|else|raise|class|const|let|var|function|await|async|new|export|default|public|private|protected)\b/;
  const stringRegex = /(["'])(?:(?=(\\?))\2.)*?\1/;
  
  let key = 0;
  while (remaining) {
    const nextKeyword = remaining.match(keywordRegex);
    const nextString = remaining.match(stringRegex);
    
    let firstMatch = null;
    let matchType = "";
    
    if (nextKeyword && (!nextString || (nextKeyword.index ?? 0) < (nextString.index ?? 0))) {
      firstMatch = nextKeyword;
      matchType = "keyword";
    } else if (nextString) {
      firstMatch = nextString;
      matchType = "string";
    }
    
    if (!firstMatch || firstMatch.index === undefined) {
      tokens.push(<span key={key++}>{remaining}</span>);
      break;
    }
    
    if (firstMatch.index > 0) {
      tokens.push(<span key={key++}>{remaining.substring(0, firstMatch.index)}</span>);
    }
    
    const matchedText = firstMatch[0];
    if (matchType === "keyword") {
      tokens.push(<span key={key++} className="syntax-keyword">{matchedText}</span>);
    } else if (matchType === "string") {
      tokens.push(<span key={key++} className="syntax-string">{matchedText}</span>);
    }
    
    remaining = remaining.substring(firstMatch.index + matchedText.length);
  }
  
  return <>{tokens}</>;
}
