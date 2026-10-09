\# Space Goats V4 \- Python AI Coding Spec Sheet

\#\# 1\. Game State & Objects  
\- \`Game\`: Manages \`Deck\`, \`Discard\_Pile\`, \`Orbital\_Area\` (list of ejected Goat cards), \`Players\` (list), \`Current\_Turn\_Index\`.  
\- \`Player\`: Manages \`Hand\` (list), \`Spaceship\` (dict containing \`Goats\` and \`Specials\` attached), \`Hand\_Limit\` (default 5).  
\- \`Card\`: Attributes: \`Type\` (Goat, Action, Block, Special), \`Name\`, \`Goat\_Count\` (int 0-3), \`Effect\_ID\` (string for logic mapping).

\#\# 2\. Turn Sequence (The Loop)  
1\. \*\*Start Phase\*\*:  
   \- Check \`Specials\` in Spaceship.  
   \- If "Hydroponic Alfalfa" is attached \-\> Player draws 1 card immediately.  
2\. \*\*Draw Phase\*\*:  
   \- Draw 1 card from \`Deck\`.  
   \- \*Trigger check:\* If the drawn card is "Hyper-Jumping Nanny", immediately place it in the \`Spaceship\` and draw 1 additional card. (This does NOT consume the action phase).  
3\. \*\*Action Phase\*\*:  
   \- Player may play exactly ONE card from their hand, OR draw one card instead.  
   \- \*Restriction Checks:\*  
     \- If playing Action against opponents, verify "Space Sickness" is not attached to this player.  
     \- If playing a Goat, verify "Quarantine Zone" is not attached to this player.  
4\. \*\*End Phase\*\*:  
   \- Player discards cards until hand size equals \`Hand\_Limit\` (Default is 5\. If "Chewed Wiring" is attached, limit is 3).

\#\# 3\. Card Execution & LIFO Stack  
All Actions and Specials use a Last-In, First-Out (LIFO) stack to allow Blocks.  
\- \`play\_card(card, target)\` puts the action on the stack.  
\- All other players have a window to play a valid \`Block\` card from their hand.  
\- \*Block Validation:\*  
   \- "Goat-Yoga Focus" ONLY blocks "Tractor Beam".  
   \- "Cardboard Forcefield" ONLY blocks "Airlock Malfunction" or "Laser Blast".  
   \- "Tin-Foil Space Helmet" ONLY blocks Specials played on a player, OR "Space Wrench".  
\- If a valid Block is played, both the Action and the Block are sent to the \`Discard\_Pile\`. The Action effect is nullified.

\#\# 4\. Keyword Effects (Action Resolution)  
\- \`EJECT\`: Remove the target Goat card from a player's Spaceship and append it to the \`Orbital\_Area\` list.  
\- \`DESTROY\`: Remove the target Goat card from a player's Spaceship and append it to the \`Discard\_Pile\`.  
\- \`STEAL\`: Remove the target Goat card from a player's Spaceship and append it to the acting player's \`Spaceship\`.  
\- \`SCOOP\`: Move all Goat cards currently in the \`Orbital\_Area\` to the acting player's \`Spaceship\`.  
\- \`REMOVE\_MODIFIER\`: Send target Special card attached to any Spaceship to the \`Discard\_Pile\`.

\#\# 5\. The Final Orbit (Endgame Condition)  
\- \*\*Trigger:\*\* The exact moment the \`Deck\` length \== 0\.  
\- \*\*Transition:\*\* Halt the normal Turn Sequence. Begin "The Final Orbit" phase.  
\- \*\*Execution:\*\*  
  \- Every player gets exactly 1 final turn, starting with the player who drew the last card.  
  \- During this final turn:  
    \- Skip Draw Phase.  
    \- Action Phase: The player may play up to 2 cards from their hand (instead of 1).  
    \- Skip End Phase (no hand limit check).  
\- \*\*Scoring:\*\* Once the final player concludes their turn, sum the \`Goat\_Count\` values of all Goats in each player's \`Spaceship\`. The highest integer wins. Tie-breaker: Highest number of cards remaining in hand.