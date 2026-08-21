import { useState } from 'react';
import {
    addTransaction, type NewTransaction
} from '../api/inventory';
import {
   validateFloatValue,
   validatePurchasePrice,
   validateSkinName, 
   validateTransactionDetails, 
   validateTransactionType,
   validateTransactionValue
} from '../utils/validation';

type TransactionTypes = "Deposit" | "Purchase" | "Withdraw" | "Sale"

const TRANSACTIONS: TransactionTypes[] = [
    "Deposit",
    "Purchase",
    "Withdraw",
    "Sale"
]

interface AddTransactionsFormProps {
    updateBalance: () => Promise<void>; 
}

interface TransactionTypeFormProps {
    typeValue: string | "";
    updateType: (typeValue: TransactionTypes) => void;
}

function TransactionTypeForm({ typeValue, updateType }: TransactionTypeFormProps) {
    return (
        <select value={typeValue} onChange={(e) => updateType(e.target.value as TransactionTypes)} style={{ padding: "6px 8px", borderRadius: 4 }}>
            <option value="" disabled>
                Select a transaction type
            </option>
            {TRANSACTIONS.map((transactionType) => (
                <option key={transactionType} value={transactionType}>
                {transactionType}
                </option>
            ))}
        </select>
    );
}

export default function AddTransactionsForm({ updateBalance }: AddTransactionsFormProps) {
    const [transactionType, setTransactionType] = useState('');
    const [transactionValue, setTransactionValue] = useState('');
    const [transactionDetails, setTransactionDetails] = useState('');
    const [validationError, setValidationError] = useState<string | null>(null);
    const [stateText, setStateText] = useState('');

    async function handleSubmit() {
        const trimmedDetails = transactionDetails.trim();
        let typeError = validateTransactionType(transactionType);
        let detailsError = validateTransactionDetails(trimmedDetails);
        let valueError = validateTransactionValue(transactionValue);
        const error = typeError ?? detailsError ?? valueError;
        setValidationError(error);

        if (error != null) {
            return
        }

        const transaction: NewTransaction = {
            transaction_details: trimmedDetails,
            transaction_type: transactionType,
            transaction_value: parseFloat(transactionValue)
        };

        const entryState = await addTransaction(transaction);
        if (entryState.status == "added") {
            setStateText(`Added transaction ${transaction.transaction_type} of value ${transaction.transaction_value} and details of ${transactionDetails} to database.`)
            updateBalance();
        }
    }
    return (
        <>
            <p>Transaction Type</p>
            <TransactionTypeForm typeValue={transactionType} updateType={setTransactionType}/>
            <p>Transaction Value</p>
            <input value={transactionValue} onChange={(event) => setTransactionValue(event.target.value)}/>
            <p>Transaction Details</p>
            <input value={transactionDetails} onChange={(event) => setTransactionDetails(event.target.value)}/>
            <button onClick={handleSubmit}>Submit Transaction</button>
            <p>{validationError}</p>
            <p>{stateText}</p>
        </>
    );
}
