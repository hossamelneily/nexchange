export default class Extractor {
    static getCurrenciesFromPair(pair, baseLength) {
        let first = pair.slice(0,baseLength);
        let second = pair.slice(baseLength);
        return [first, second];
    }

    static getTitleFromPair(pair, baseLength) {
    	let currencies = this.getCurrenciesFromPair(pair, baseLength);
    	return `${currencies[0]}/${currencies[1]}`;
    }

    static reversePair(pair, baseLength) {
    	let currencies = this.getCurrenciesFromPair(pair, baseLength);
    	return `${currencies[1]}${currencies[0]}`;
    }
}