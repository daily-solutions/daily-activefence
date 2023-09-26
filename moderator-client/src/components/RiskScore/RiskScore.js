import React, { useState, useEffect } from 'react';
import { useAppMessage } from '@daily-co/daily-react';
import './RiskScore.css';

export default function RiskScore({ id }) {
  const [myScores, setMyScores] = useState();

  useAppMessage({
    onAppMessage: (ev) => {
      console.log(
        'my id: ',
        id,
        ', all risk scores: ',
        ev.data.riskScores,
        ', my risk scores: ',
        ev.data.riskScores[id],
      );
      console.log('keys: ', Object.keys(ev.data.riskScores));
      console.log(
        'Find my ID in the keys: ',
        Object.keys(ev.data.riskScores).find((e) => e === id),
      );
      if (ev.data.riskScores[id]) {
        console.info('!!! setting my scores to:', ev.data.riskScores[id]);
        setMyScores(ev.data.riskScores[id]);
      }
    },
  });

  useEffect(() => {
    if (myScores) {
      console.info(
        'My alcohol score:',
        myScores['unauthorised_sales.alcohol'],
        ', my weapons score:',
        myScores['unauthorised_sales.weapons'],
      );
    }
  }, [myScores]);

  /*
  const heightFor = (score) => {
    const scoreNames = {
      alcohol: 'unauthorised_sales.alcohol',
      weapons: 'unauthorised_sales.weapons',
    };

    let scorePct;
    if (myScores && scoreNames[score] in myScores) {
      scorePct = myScores[scoreNames[score]];
    } else {
      scorePct = 0;
    }
    return `${Math.round(scorePct * 100.0)}%`;
  };
  */

  return (
    <div className="riskScores">
      {myScores && myScores['unauthorised_sales.alcohol'] > 0.9 && (
        <div className="riskScore success">
          <div className="riskLabel">🍻 Cheers! 🍸</div>
        </div>
      )}
      {myScores && myScores['unauthorised_sales.weapons'] > 0.9 && (
        <div className="riskScore warning">
          <div className="riskLabel">🔫 Weapon Detected! ⚠️</div>
        </div>
      )}
    </div>
  );
}
