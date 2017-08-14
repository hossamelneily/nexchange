export default class Extractor {
    static getCurrenciesFromPair(pair) {
        let first = pair.slice(0,3);
        let second = pair.slice(3,6);
        return [first, second];
    }

    static getTitleFromPair(pair) {
    	let currencies = this.getCurrenciesFromPair(pair);
    	return `${currencies[0]}/${currencies[1]}`;
    }

    static reversePair(pair) {
    	let currencies = this.getCurrenciesFromPair(pair);    	
    	return `${currencies[1]}${currencies[0]}`;
    }
}