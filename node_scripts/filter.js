const Web3 = require('web3');
const fetch = require("node-fetch");
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

const ROUND_DURATION_MS = 300 * 1000
const TIME_OF_BETTING_MS = ROUND_DURATION_MS - 10 * 1000

let current_interval = 1000
let current_active_lock_at = null
let logged_payout = false

let current_active_round_id = null
let totalBull = 0
let totalBear = 0
let totalBets = 0
let totalBetsCopy = 0
let pancakeBullPayout = 0
let pancakeBearPayout = 0
let finalBullPayout = 0
let finalBearPayout = 0
let payout_bull = 0
let payout_bear = 0
let payout_bull_at_betting = 0
let payout_bear_at_betting = 0


const csvWriter = createCsvWriter({
  path: 'payout_calc.csv',
  header: [
      {id: 'round_id', title: 'ROUND ID'},
      {id: 'pancake_bull', title: 'PANCAKE BULL'},
      {id: 'pancake_bear', title: 'PANCAKE BEAR'},
      {id: 'coqui_bull', title: 'COQUI BULL'},
      {id: 'coqui_bear', title: 'COQUI BEAR'},
      {id: 'final_bull', title: 'FINAL BULL'},
      {id: 'final_bear', title: 'FINAL BEAR'},
      {id: 'total_bets_pancake', title: 'TOTAL BETS PANCAKE'},
      {id: 'total_bets_script', title: 'TOTAL BETS SCRIPT'},
  ]
});


const get_pancake_last_rounds = async (first, skip, getPancakePayout = false) => {
    fetch('https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: JSON.stringify({query: `{ rounds(
                first: ${first},
                skip: ${skip},
                orderBy: epoch,
                orderDirection: desc
            ){
                id
                epoch
                startAt
                bullBets
                bullAmount
                bearBets
                bearAmount
                lockAt
                lockPrice
                totalBets
                endAt
              } }`})
          })
            .then(r => r.json())
            .then(data => {
              let bullAmount = parseFloat(data.data.rounds[1].bullAmount)
              let bearAmount = parseFloat(data.data.rounds[1].bearAmount)

              if(current_active_round_id !== data.data.rounds[1].id) {
                totalBets = 0
                totalBull = 0
                totalBear = 0
                logged_payout = false
                finalBullPayout = bearAmount / bullAmount + 1;
                finalBearPayout = bullAmount / bearAmount + 1;
                const csv_data = {
                  round_id: data.data.rounds[1].id,
                  pancake_bull: pancakeBullPayout,
                  pancake_bear: pancakeBearPayout,
                  coqui_bull: payout_bull_at_betting,
                  coqui_bear: payout_bear_at_betting,
                  final_bull: finalBullPayout,
                  final_bear: finalBearPayout,
                  total_bets_pancake: data.data.rounds[1].totalBets,
                  total_bets_script: totalBetsCopy
                }
                csvWriter.writeRecords([csv_data])       // returns a promise
                .then(() => {
                    console.log('...Done');
                    totalBetsCopy = 0
                });
                console.log('data.data.rounds[1].id', data.data.rounds[1].id)
                console.log('bear at betting', payout_bear_at_betting, '\n', 'bull at betting', payout_bull_at_betting, '\n')
                console.log('pancake bear', pancakeBearPayout, '\n', 'pancake bull', pancakeBullPayout, '\n')
                console.log('final bear', finalBearPayout, '\n', 'final bull', finalBullPayout)
                console.log('totalBets', totalBets)
              }
              current_active_round_id = data.data.rounds[1].id
              current_active_lock_at = data.data.rounds[1].lockAt
              

              if(getPancakePayout) {
                pancakeBullPayout = bearAmount / bullAmount + 1;
                pancakeBearPayout = bullAmount / bearAmount + 1;
              }
            })
}

setInterval(() => {
  if(current_active_round_id == null) {
    get_pancake_last_rounds(2,0);
  } else {
 
    if(Date.now() > parseFloat(current_active_lock_at) * 1000 + (ROUND_DURATION_MS)) {
      get_pancake_last_rounds(2,0);
    } else {
      payout_bull = parseFloat(totalBear / totalBull)
      payout_bear = parseFloat(totalBull / totalBear)
        // console.log('payout_bull', payout_bull + 1)
        // console.log('payout_bear', payout_bear + 1)
    }
    if(Date.now() > parseFloat(current_active_lock_at) * 1000 + (TIME_OF_BETTING_MS) && !logged_payout) {
      logged_payout = true
      payout_bull = parseFloat(totalBear / totalBull)
      payout_bear = parseFloat(totalBull / totalBear)
      payout_bull_at_betting = payout_bull + 1
      payout_bear_at_betting = payout_bear + 1
      get_pancake_last_rounds(2,0,true)
      // console.log('10 seconds')
      // console.log('payout_bear', payout_bear + 1)
      // console.log('payout_bull', payout_bull + 1)

    }
  }
}, current_interval);

const checkBlock = async(pancake) => {
    let web3 = new Web3('wss://bsc-ws-node.nariox.org:443');
    subscription = web3.eth.subscribe('pendingTransactions', function (error, result) {})
    .on("data", function (transactionHash) {
        web3.eth.getTransaction(transactionHash)
        .then(function (transaction) {
            if(transaction?.blockHash == null) {
                if (transaction?.to == pancake && (transaction?.input == '0x821daba1'|| transaction.input == '0x0088160f')) {
                    totalBets += 1;
                    totalBetsCopy = totalBets
                    if(transaction?.input == '0x821daba1') {
                      totalBull += parseInt(transaction?.value)
                    } else {
                      totalBear += parseInt(transaction?.value)
                    }
                    console.log('totalBets', totalBets)
                }
            }
        });
    })
}


checkBlock('0x516ffd7D1e0Ca40b1879935B2De87cb20Fc1124b')