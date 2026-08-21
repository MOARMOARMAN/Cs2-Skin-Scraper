interface CurrentBalanceInformation {
    currentBalance: number;
}

export default function DisplayBalanceInformation({currentBalance}: CurrentBalanceInformation) {
    return (
        <>
            <p>Current Balance: ${currentBalance}</p>
        </>
    );
}